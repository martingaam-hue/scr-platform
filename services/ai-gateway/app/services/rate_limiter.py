"""Redis-based rate limiting per org tier."""
import time
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

logger = structlog.get_logger()

TIER_LIMITS: dict[str, dict[str, int]] = {
    "foundation": {
        "requests_per_hour": settings.RATE_LIMIT_FOUNDATION_RPH,
        "tokens_per_day": settings.RATE_LIMIT_FOUNDATION_TPD,
    },
    "professional": {
        "requests_per_hour": settings.RATE_LIMIT_PROFESSIONAL_RPH,
        "tokens_per_day": settings.RATE_LIMIT_PROFESSIONAL_TPD,
    },
    "enterprise": {
        "requests_per_hour": settings.RATE_LIMIT_ENTERPRISE_RPH,
        "tokens_per_day": settings.RATE_LIMIT_ENTERPRISE_TPD,
    },
}


class RateLimiter:
    """Redis sliding-window rate limiter."""

    def __init__(self) -> None:
        self._redis: Any | None = None

    def _get_redis(self) -> Any:
        if self._redis is None:
            self._redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def check_and_increment(self, org_id: str, tier: str = "professional") -> None:
        """Check rate limit and increment counter. Raises ValueError if exceeded."""
        limits = TIER_LIMITS.get(tier, TIER_LIMITS["professional"])
        rph = limits["requests_per_hour"]

        redis = self._get_redis()
        hour_bucket = int(time.time()) // 3600
        key = f"ratelimit:{org_id}:hour:{hour_bucket}"

        try:
            pipe = redis.pipeline()
            pipe.incr(key)
            pipe.expire(key, 3600)
            results = await pipe.execute()
            current = results[0]

            if current > rph:
                logger.warning("rate_limit_exceeded", org_id=org_id, tier=tier, count=current, limit=rph)
                raise ValueError(
                    f"Rate limit exceeded: {current}/{rph} requests this hour for tier '{tier}'. "
                    "Upgrade your plan or wait until the next hour."
                )
        except ValueError:
            raise
        except Exception as e:
            logger.warning("rate_limiter_error", error=str(e))
            # Don't block on Redis errors

    async def get_usage(self, org_id: str) -> dict[str, int]:
        """Get current usage counts for an org."""
        redis = self._get_redis()
        hour_bucket = int(time.time()) // 3600
        day_bucket = int(time.time()) // 86400
        hour_key = f"ratelimit:{org_id}:hour:{hour_bucket}"
        day_key = f"ratelimit:{org_id}:tokens:{day_bucket}"

        try:
            hour_count = await redis.get(hour_key)
            day_tokens = await redis.get(day_key)
            return {
                "requests_this_hour": int(hour_count or 0),
                "tokens_today": int(day_tokens or 0),
            }
        except Exception:
            return {"requests_this_hour": 0, "tokens_today": 0}

    async def add_token_usage(self, org_id: str, tokens: int) -> None:
        """Increment token usage counter for daily limit tracking."""
        redis = self._get_redis()
        day_bucket = int(time.time()) // 86400
        key = f"ratelimit:{org_id}:tokens:{day_bucket}"
        try:
            pipe = redis.pipeline()
            pipe.incrby(key, tokens)
            pipe.expire(key, 86400)
            await pipe.execute()
        except Exception as e:
            logger.warning("token_tracking_error", error=str(e))
