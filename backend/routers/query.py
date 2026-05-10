# See: specs/backend/query-endpoint.md
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth.jwt import TokenData, verify_token
from ..models.db import CacheEntry, RequestLog, get_db
from ..models.schemas import QueryRequest, QueryResponse
from ..services import openai_service, redis_service, sanitizer
from ..services.faiss_service import faiss_service

logger = logging.getLogger(__name__)
router = APIRouter()

_SIMILARITY_THRESHOLD = 0.9


async def _log_request(
    db: AsyncSession,
    user_id: str,
    team_id: str | None,
    query_hash: str,
    cache_hit: bool,
    tokens_used: int,
) -> None:
    """Persist a request log row (called as background task)."""
    log = RequestLog(
        user_id=user_id,
        team_id=team_id,
        query_hash=query_hash,
        cache_hit=cache_hit,
        tokens_used=tokens_used,
    )
    db.add(log)
    await db.commit()


@router.post("", response_model=QueryResponse)
async def query(
    req: QueryRequest,
    background_tasks: BackgroundTasks,
    token: TokenData = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """Cache-first query: Redis → FAISS → OpenAI fallback."""

    # 1. Sanitize before any processing
    clean_query = sanitizer.sanitize(req.query)
    if not clean_query.strip():
        raise HTTPException(status_code=422, detail="Query is empty after sanitization")

    # 2. Derive cache key
    query_hash = redis_service.make_key(clean_query)

    # 3. Redis hot cache check
    cached = await redis_service.get(query_hash)
    if cached:
        logger.info("Redis HIT  hash=%s user=%s", query_hash[:8], token.user_id)
        background_tasks.add_task(
            _log_request, db, token.user_id, token.team_id, query_hash, True, 0
        )
        return QueryResponse(
            response=cached,
            cache_hit=True,
            tokens_used=0,
            prompt_type=req.prompt_type,
        )

    # 4. FAISS semantic search
    pg_id, similarity = await faiss_service.search(clean_query)
    if pg_id and similarity >= _SIMILARITY_THRESHOLD:
        result = await db.get(CacheEntry, pg_id)
        if result:
            logger.info("FAISS HIT  sim=%.3f hash=%s", similarity, query_hash[:8])
            await redis_service.set(query_hash, result.response)
            background_tasks.add_task(
                _log_request, db, token.user_id, token.team_id, query_hash, True, 0
            )
            return QueryResponse(
                response=result.response,
                cache_hit=True,
                similarity=similarity,
                tokens_used=0,
                prompt_type=req.prompt_type,
            )

    # 5. OpenAI fallback
    prompt = clean_query
    if req.context:
        prompt = f"Context:\n{sanitizer.sanitize(req.context)}\n\nQuestion:\n{clean_query}"

    try:
        response_text, tokens_used = await openai_service.complete(
            prompt, req.prompt_type.value
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    logger.info("OpenAI MISS hash=%s tokens=%d", query_hash[:8], tokens_used)

    # 6. Store result in background (non-blocking)
    background_tasks.add_task(
        _store_result,
        clean_query,
        response_text,
        query_hash,
        token.user_id,
        token.team_id,
        tokens_used,
        db,
    )
    background_tasks.add_task(
        _log_request, db, token.user_id, token.team_id, query_hash, False, tokens_used
    )

    return QueryResponse(
        response=response_text,
        cache_hit=False,
        tokens_used=tokens_used,
        prompt_type=req.prompt_type,
    )


async def _store_result(
    query: str,
    response: str,
    query_hash: str,
    user_id: str,
    team_id: str | None,
    tokens_used: int,
    db: AsyncSession,
) -> None:
    """Upsert cache entry to Postgres, FAISS, and Redis."""
    from sqlalchemy import select

    # Idempotent: skip if already stored
    existing = await db.execute(
        select(CacheEntry).where(CacheEntry.query_hash == query_hash)
    )
    if existing.scalar_one_or_none():
        return

    entry = CacheEntry(
        user_id=user_id,
        team_id=team_id,
        query_hash=query_hash,
        query=query,
        response=response[:10_000],
        tokens_saved=tokens_used,
        model_used="gpt-4.1-mini",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    await faiss_service.add(query, str(entry.id))
    await redis_service.set(query_hash, response)
