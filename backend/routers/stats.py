# See: specs/backend/stats-endpoint.md
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.jwt import TokenData, verify_token
from ..models.db import CacheEntry, RequestLog, get_db
from ..models.schemas import StatsHistoryPoint, StatsResponse

router = APIRouter()


@router.get("", response_model=StatsResponse)
async def get_stats(
    team_id: Optional[str] = Query(None),
    token: TokenData = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
) -> StatsResponse:
    """Aggregate cache + request statistics for the current user / team scope."""

    scope_user = token.user_id
    scope_team = team_id or token.team_id

    # Total cache entries
    entry_stmt = select(func.count(CacheEntry.id), func.coalesce(func.sum(CacheEntry.tokens_saved), 0))
    if scope_team:
        entry_stmt = entry_stmt.where(CacheEntry.team_id == scope_team)
    else:
        entry_stmt = entry_stmt.where(CacheEntry.user_id == scope_user)
    entry_result = (await db.execute(entry_stmt)).one()
    total_entries: int = entry_result[0]
    tokens_saved: int = entry_result[1]

    # Request logs
    log_base = select(RequestLog)
    if scope_team:
        log_base = log_base.where(RequestLog.team_id == scope_team)
    else:
        log_base = log_base.where(RequestLog.user_id == scope_user)

    total_req_stmt = select(func.count(RequestLog.id))
    hits_stmt = select(func.count(RequestLog.id)).where(RequestLog.cache_hit.is_(True))

    if scope_team:
        total_req_stmt = total_req_stmt.where(RequestLog.team_id == scope_team)
        hits_stmt = hits_stmt.where(RequestLog.team_id == scope_team)
    else:
        total_req_stmt = total_req_stmt.where(RequestLog.user_id == scope_user)
        hits_stmt = hits_stmt.where(RequestLog.user_id == scope_user)

    total_requests: int = (await db.execute(total_req_stmt)).scalar_one()
    cache_hits: int = (await db.execute(hits_stmt)).scalar_one()
    cache_misses = total_requests - cache_hits
    hit_ratio = cache_hits / total_requests if total_requests > 0 else 0.0

    return StatsResponse(
        total_entries=total_entries,
        total_requests=total_requests,
        cache_hits=cache_hits,
        cache_misses=cache_misses,
        hit_ratio=round(hit_ratio, 4),
        tokens_saved=tokens_saved,
    )


@router.get("/history", response_model=list[StatsHistoryPoint])
async def get_stats_history(
    days: int = Query(30, ge=1, le=365),
    token: TokenData = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
) -> list[StatsHistoryPoint]:
    """Daily time-series of requests, hits, and tokens saved for the past N days."""

    scope_user = token.user_id
    scope_team = token.team_id
    since = datetime.utcnow() - timedelta(days=days)

    stmt = (
        select(
            func.date(RequestLog.created_at).label("day"),
            func.count(RequestLog.id).label("requests"),
            func.sum(func.cast(RequestLog.cache_hit, Integer)).label("hits"),
        )
        .where(RequestLog.created_at >= since)
        .group_by(func.date(RequestLog.created_at))
        .order_by(func.date(RequestLog.created_at))
    )
    if scope_team:
        stmt = stmt.where(RequestLog.team_id == scope_team)
    else:
        stmt = stmt.where(RequestLog.user_id == scope_user)

    rows = (await db.execute(stmt)).all()

    # Build a dict keyed by date string for gap-filling
    data: dict[str, StatsHistoryPoint] = {}
    for row in rows:
        d = str(row.day)
        data[d] = StatsHistoryPoint(
            date=d,
            requests=row.requests or 0,
            cache_hits=int(row.hits or 0),
            tokens_saved=0,  # tokens_saved is on CacheEntry, not RequestLog
        )

    # Fill missing days with zeros
    result: list[StatsHistoryPoint] = []
    for i in range(days):
        day = (datetime.utcnow() - timedelta(days=days - 1 - i)).date()
        day_str = str(day)
        result.append(data.get(day_str, StatsHistoryPoint(date=day_str, requests=0, cache_hits=0, tokens_saved=0)))

    return result
