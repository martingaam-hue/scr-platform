"""AI Gateway circuit breaker — Redis-backed state shared across API workers.

States
------
CLOSED    Normal operation — all requests pass through.
OPEN      Gateway unhealthy — requests blocked immediately (fast-fail).
HALF_OPEN Recovery probe — one request allowed; closes on success, re-opens on failure.

State transitions
-----------------
CLOSED  → OPEN      after ``failure_threshold`` consecutive failures
OPEN    → HALF_OPEN after ``recovery_timeout`` seconds have elapsed
HALF_OPEN → CLOSED  on probe success
HALF_OPEN → OPEN    on probe failure (recovery timer resets)

Storage
-------
State is persisted in Redis under ``circuit_breaker:ai_gateway`` as a JSON blob
with TTL=300 s so every API worker shares the same view.  If Redis is unavailable
the instance falls back to its in-memory copy — safe for single-process deploys.
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from typing import Any

import structlog

logger = structlog.get_logger()

# ── Constants ─────────────────────────────────────────────────────────────────

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half_open"

_REDIS_KEY = "circuit_breaker:ai_gateway"
_REDIS_TTL = 300  # seconds — auto-recover if Redis loses the key


# ── Exception ─────────────────────────────────────────────────────────────────


class AIGatewayUnavailableError(Exception):
    """Raised when the AI Gateway circuit breaker is OPEN (or HALF_OPEN probe fails)."""

    def __init__(
        self,
        message: str = "AI service temporarily unavailable. Please try again shortly.",
        retry_after: int = 60,
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after


# ── Circuit Breaker ───────────────────────────────────────────────────────────


class CircuitBreaker:
    """Redis-backed circuit breaker for the SCR Platform AI Gateway."""

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
        success_threshold: int = 1,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        # In-memory fallback state (used when Redis is unavailable)
        self._mem: dict[str, Any] = {
            "state": CLOSED,
            "failure_count": 0,
            "last_failure_time": None,
            "last_state_change": time.time(),
        }

    # ── Public API ────────────────────────────────────────────────────────────

    async def allow_request(self) -> bool:
        """Return True if a request to the AI Gateway should proceed."""
        sd = await self._load()
        state = sd["state"]
        now = time.time()

        if state == CLOSED:
            return True

        if state == OPEN:
            # Check whether the recovery window has elapsed → probe
            reference = sd.get("last_failure_time") or sd["last_state_change"]
            if (now - reference) >= self.recovery_timeout:
                await self._save({**sd, "state": HALF_OPEN, "last_state_change": now})
                logger.info(
                    "circuit_breaker.half_open",
                    msg="Circuit breaker HALF_OPEN — probing AI Gateway",
                )
                return True
            return False

        # HALF_OPEN — let the single probe through
        return True

    async def record_success(self) -> None:
        """Call after a successful AI Gateway response."""
        sd = await self._load()
        state = sd["state"]
        now = time.time()

        if state == HALF_OPEN:
            await self._save(
                {
                    **sd,
                    "state": CLOSED,
                    "failure_count": 0,
                    "last_failure_time": None,
                    "last_state_change": now,
                }
            )
            logger.info(
                "circuit_breaker.closed",
                msg="Circuit breaker CLOSED — AI Gateway recovered",
            )
        elif state == CLOSED and sd["failure_count"] > 0:
            # Reset rolling failure counter on any success
            await self._save({**sd, "failure_count": 0, "last_failure_time": None})

    async def record_failure(self) -> None:
        """Call after a failed AI Gateway request (timeout / connection error)."""
        sd = await self._load()
        state = sd["state"]
        now = time.time()

        if state == HALF_OPEN:
            # Probe failed → back to OPEN, reset recovery timer
            await self._save(
                {
                    **sd,
                    "state": OPEN,
                    "last_failure_time": now,
                    "last_state_change": now,
                }
            )
            logger.warning(
                "circuit_breaker.opened",
                msg="Circuit breaker OPENED — AI Gateway probe failed, resetting 60 s timer",
            )

        elif state == CLOSED:
            new_count = sd["failure_count"] + 1
            if new_count >= self.failure_threshold:
                await self._save(
                    {
                        **sd,
                        "state": OPEN,
                        "failure_count": new_count,
                        "last_failure_time": now,
                        "last_state_change": now,
                    }
                )
                logger.warning(
                    "circuit_breaker.opened",
                    msg="Circuit breaker OPENED — AI Gateway failures exceeded threshold",
                    failure_count=new_count,
                )
            else:
                await self._save({**sd, "failure_count": new_count, "last_failure_time": now})

    async def get_status(self) -> dict[str, Any]:
        """Return a dict suitable for the /health/ai endpoint."""
        sd = await self._load()
        last_failure = sd.get("last_failure_time")
        return {
            "circuit_state": sd["state"],
            "failure_count": sd["failure_count"],
            "last_failure": (
                datetime.fromtimestamp(last_failure, tz=UTC).isoformat() if last_failure else None
            ),
            "ai_gateway_healthy": sd["state"] == CLOSED,
        }

    # ── Redis helpers ─────────────────────────────────────────────────────────

    async def _load(self) -> dict[str, Any]:
        """Load state from Redis; fall back to in-memory copy if Redis fails."""
        try:
            import redis.asyncio as aioredis

            from app.core.config import settings

            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            raw = await r.get(_REDIS_KEY)
            await r.aclose()
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return dict(self._mem)

    async def _save(self, sd: dict[str, Any]) -> None:
        """Persist state to Redis and update in-memory fallback."""
        self._mem = dict(sd)
        try:
            import redis.asyncio as aioredis

            from app.core.config import settings

            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await r.set(_REDIS_KEY, json.dumps(sd), ex=_REDIS_TTL)
            await r.aclose()
        except Exception:
            pass  # In-memory already updated; Redis unavailable is acceptable


# ── Module-level singleton ────────────────────────────────────────────────────
# Import this wherever an AI Gateway httpx call is made.

ai_gateway_cb = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=60,
    success_threshold=1,
)
