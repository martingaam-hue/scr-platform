"""HTTP response caching via Redis with TTL-based invalidation."""
from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis


def cache_key(prefix: str, org_id: str, *args: Any) -> str:
    """Build a deterministic cache key scoped to the org."""
    parts = [prefix, org_id] + [str(a) for a in args]
    return ":".join(parts)


async def get_cached(key: str) -> Any | None:
    """Return parsed JSON from cache or None on miss/error."""
    try:
        r = await get_redis()
        raw = await r.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("Cache GET error: %s", exc)
        return None


async def set_cached(key: str, value: Any, ttl: int = 300) -> None:
    """JSON-serialise value and store with TTL (seconds). Silently fails."""
    try:
        r = await get_redis()
        await r.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as exc:
        logger.warning("Cache SET error: %s", exc)


async def invalidate(prefix: str, org_id: str) -> None:
    """Delete all cache keys matching the org+prefix pattern."""
    try:
        r = await get_redis()
        pattern = f"{prefix}:{org_id}:*"
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
    except Exception as exc:
        logger.warning("Cache invalidate error: %s", exc)
