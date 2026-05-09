# See: specs/backend/upsert-endpoint.md
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.jwt import TokenData, verify_token
from ..models.db import CacheEntry, get_db
from ..models.schemas import CacheEntryDTO, UpsertRequest, UpsertResponse
from ..services import redis_service, sanitizer
from ..services.faiss_service import faiss_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=UpsertResponse, status_code=status.HTTP_201_CREATED)
async def upsert(
    req: UpsertRequest,
    token: TokenData = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
) -> UpsertResponse:
    """Store a query-response pair into FAISS + Postgres + Redis."""

    clean_query = sanitizer.sanitize(req.query)
    if not clean_query.strip():
        raise HTTPException(status_code=422, detail="Query is empty after sanitization")

    query_hash = redis_service.make_key(clean_query)

    # Idempotent: return existing entry if hash already exists
    result = await db.execute(
        select(CacheEntry).where(CacheEntry.query_hash == query_hash)
    )
    existing = result.scalar_one_or_none()
    if existing:
        return UpsertResponse(
            id=str(existing.id),
            query_hash=query_hash,
            message="Already exists",
        )

    entry = CacheEntry(
        user_id=token.user_id,
        team_id=token.team_id,
        query_hash=query_hash,
        query=clean_query,
        response=req.response[:10_000],
        tokens_saved=req.tokens_saved,
        model_used=req.model_used,
    )
    db.add(entry)
    try:
        await db.commit()
        await db.refresh(entry)
    except Exception as exc:
        await db.rollback()
        logger.error("Postgres insert failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to persist cache entry")

    # Add to FAISS + Redis only after successful DB commit
    await faiss_service.add(clean_query, str(entry.id))
    await redis_service.set(query_hash, req.response)

    logger.info("Upserted hash=%s user=%s", query_hash[:8], token.user_id)
    return UpsertResponse(id=str(entry.id), query_hash=query_hash)


@router.get("", response_model=list[CacheEntryDTO])
async def list_cache(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user_id: str | None = Query(None),
    team_id: str | None = Query(None),
    token: TokenData = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
) -> list[CacheEntryDTO]:
    """Paginated list of cache entries, filterable by user/team."""
    stmt = select(CacheEntry)

    if user_id:
        stmt = stmt.where(CacheEntry.user_id == user_id)
    elif team_id:
        stmt = stmt.where(CacheEntry.team_id == team_id)
    else:
        stmt = stmt.where(CacheEntry.user_id == token.user_id)

    stmt = stmt.order_by(CacheEntry.created_at.desc())
    stmt = stmt.offset((page - 1) * limit).limit(limit)

    result = await db.execute(stmt)
    entries = result.scalars().all()
    return [
        CacheEntryDTO(
            id=str(e.id),
            user_id=e.user_id,
            team_id=e.team_id,
            query=e.query,
            response=e.response,
            tokens_saved=e.tokens_saved,
            model_used=e.model_used,
            created_at=e.created_at,
        )
        for e in entries
    ]
