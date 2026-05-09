# See: specs/backend/query-endpoint.md — Redis Hot Cache
import hashlib
import logging
import os
from typing import Optional

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

_REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_TTL_SECONDS: int = 60 * 60 * 24  # 24 hours

_client: Optional[aioredis.Redis] = None


def _get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(_REDIS_URL, decode_responses=True)
    return _client


def make_key(query: str) -> str:
    """SHA-256 hash of sanitized query — used as Redis key and Postgres query_hash."""
    return hashlib.sha256(query.encode("utf-8")).hexdigest()


async def get(query_hash: str) -> Optional[str]:
    """Return cached response for *query_hash*, or None on miss/error."""
    try:
        return await _get_client().get(query_hash)
    except Exception as exc:
        logger.warning("Redis GET failed (degrading gracefully): %s", exc)
        return None


async def set(query_hash: str, response: str) -> None:
    """Cache *response* under *query_hash* with 24h TTL."""
    try:
        await _get_client().set(query_hash, response, ex=_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Redis SET failed (degrading gracefully): %s", exc)


async def delete(query_hash: str) -> None:
    """Remove a single cached entry."""
    try:
        await _get_client().delete(query_hash)
    except Exception as exc:
        logger.warning("Redis DEL failed: %s", exc)
