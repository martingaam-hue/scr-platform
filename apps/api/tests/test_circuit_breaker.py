"""Unit tests for the AI Gateway circuit breaker.

No DB, no network, no real Redis required — all external I/O is mocked.
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.circuit_breaker import (
    _REDIS_KEY,
    _REDIS_TTL,
    CLOSED,
    HALF_OPEN,
    OPEN,
    AIGatewayUnavailableError,
    CircuitBreaker,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_cb(**kwargs) -> CircuitBreaker:
    """Return a fresh CircuitBreaker with default test params."""
    return CircuitBreaker(failure_threshold=3, recovery_timeout=60, **kwargs)


def _redis_state(
    state: str = CLOSED,
    failure_count: int = 0,
    last_failure_time: float | None = None,
    last_state_change: float | None = None,
) -> str:
    return json.dumps(
        {
            "state": state,
            "failure_count": failure_count,
            "last_failure_time": last_failure_time,
            "last_state_change": last_state_change or time.time(),
        }
    )


def _mock_redis(raw: str | None = None) -> MagicMock:
    """Return a mock redis client that returns ``raw`` from GET."""
    r = AsyncMock()
    r.get = AsyncMock(return_value=raw)
    r.set = AsyncMock()
    r.aclose = AsyncMock()
    return r


# ── CLOSED → OPEN after failure_threshold failures ────────────────────────────


class TestClosedToOpen:
    async def test_closed_allows_requests(self):
        cb = _make_cb()
        with patch("redis.asyncio.from_url", return_value=_mock_redis(None)):
            assert await cb.allow_request() is True

    async def test_two_failures_stay_closed(self):
        cb = _make_cb()
        with patch("redis.asyncio.from_url", return_value=_mock_redis(None)):
            await cb.record_failure()
            await cb.record_failure()
            assert await cb.allow_request() is True

    async def test_third_failure_trips_open(self):
        cb = _make_cb()
        saved: list[dict] = []

        def fake_from_url(*a, **kw):
            r = AsyncMock()
            r.get = AsyncMock(side_effect=lambda k: saved[-1] if saved else None)

            async def fake_set(k, v, ex=None):
                saved.append(json.loads(v))

            r.set = fake_set
            r.aclose = AsyncMock()
            return r

        with patch("redis.asyncio.from_url", side_effect=fake_from_url):
            await cb.record_failure()
            await cb.record_failure()
            await cb.record_failure()

        assert saved[-1]["state"] == OPEN

    async def test_open_blocks_requests(self):
        cb = _make_cb()
        raw = _redis_state(state=OPEN, last_failure_time=time.time())
        with patch("redis.asyncio.from_url", return_value=_mock_redis(raw)):
            assert await cb.allow_request() is False

    async def test_open_blocks_without_making_http_call(self):
        """If CB is open, no httpx call should be attempted."""
        import httpx

        cb = _make_cb()
        raw = _redis_state(state=OPEN, last_failure_time=time.time())

        call_count = 0

        async def fake_post(*a, **kw):
            nonlocal call_count
            call_count += 1
            raise AssertionError("httpx.post must NOT be called when circuit is open")

        with (
            patch("redis.asyncio.from_url", return_value=_mock_redis(raw)),
            patch.object(httpx.AsyncClient, "post", fake_post),
        ):
            assert await cb.allow_request() is False

        assert call_count == 0


# ── OPEN → HALF_OPEN after recovery_timeout ────────────────────────────────────


class TestOpenToHalfOpen:
    async def test_open_transitions_to_half_open_after_timeout(self):
        cb = _make_cb()
        # last_failure_time is 61 seconds in the past → recovery window has elapsed
        raw = _redis_state(state=OPEN, last_failure_time=time.time() - 61)
        saved: list[dict] = []

        r = _mock_redis(raw)

        async def fake_set(k, v, ex=None):
            saved.append(json.loads(v))

        r.set = fake_set

        with patch("redis.asyncio.from_url", return_value=r):
            result = await cb.allow_request()

        assert result is True
        assert saved[-1]["state"] == HALF_OPEN

    async def test_open_stays_open_before_timeout(self):
        cb = _make_cb()
        raw = _redis_state(state=OPEN, last_failure_time=time.time() - 30)
        with patch("redis.asyncio.from_url", return_value=_mock_redis(raw)):
            assert await cb.allow_request() is False


# ── HALF_OPEN → CLOSED on probe success ────────────────────────────────────────


class TestHalfOpenToClosedOnSuccess:
    async def test_success_in_half_open_closes_breaker(self):
        cb = _make_cb()
        raw = _redis_state(state=HALF_OPEN)
        saved: list[dict] = []

        r = _mock_redis(raw)

        async def fake_set(k, v, ex=None):
            saved.append(json.loads(v))

        r.set = fake_set

        with patch("redis.asyncio.from_url", return_value=r):
            await cb.record_success()

        assert saved[-1]["state"] == CLOSED
        assert saved[-1]["failure_count"] == 0

    async def test_closed_breaker_allows_requests_after_recovery(self):
        cb = _make_cb()
        closed_raw = _redis_state(state=CLOSED)
        with patch("redis.asyncio.from_url", return_value=_mock_redis(closed_raw)):
            assert await cb.allow_request() is True


# ── HALF_OPEN → OPEN on probe failure ─────────────────────────────────────────


class TestHalfOpenToOpenOnFailure:
    async def test_failure_in_half_open_reopens_breaker(self):
        cb = _make_cb()
        raw = _redis_state(state=HALF_OPEN)
        saved: list[dict] = []

        r = _mock_redis(raw)

        async def fake_set(k, v, ex=None):
            saved.append(json.loads(v))

        r.set = fake_set

        with patch("redis.asyncio.from_url", return_value=r):
            await cb.record_failure()

        assert saved[-1]["state"] == OPEN

    async def test_failure_in_half_open_resets_timer(self):
        cb = _make_cb()
        old_time = time.time() - 100
        raw = _redis_state(state=HALF_OPEN, last_state_change=old_time)
        saved: list[dict] = []

        r = _mock_redis(raw)

        async def fake_set(k, v, ex=None):
            saved.append(json.loads(v))

        r.set = fake_set

        before = time.time()
        with patch("redis.asyncio.from_url", return_value=r):
            await cb.record_failure()
        after = time.time()

        new_failure_time = saved[-1]["last_failure_time"]
        assert before <= new_failure_time <= after


# ── Redis state sharing across instances ──────────────────────────────────────


class TestRedisStateSharing:
    async def test_two_instances_share_state_via_redis(self):
        """Two CircuitBreaker instances reading the same Redis key see the same state."""
        shared_store: dict[str, str] = {}

        def make_redis():
            r = AsyncMock()

            async def fake_get(k):
                return shared_store.get(k)

            async def fake_set(k, v, ex=None):
                shared_store[k] = v

            r.get = fake_get
            r.set = fake_set
            r.aclose = AsyncMock()
            return r

        cb1 = _make_cb()
        cb2 = _make_cb()

        with patch("redis.asyncio.from_url", side_effect=lambda *a, **kw: make_redis()):
            # cb1 trips the breaker
            await cb1.record_failure()
            await cb1.record_failure()
            await cb1.record_failure()

            # cb2 should see OPEN state from Redis
            result = await cb2.allow_request()

        assert result is False

    async def test_set_uses_correct_key_and_ttl(self):
        saved_calls: list[tuple] = []

        r = AsyncMock()
        r.get = AsyncMock(return_value=None)

        async def fake_set(k, v, ex=None):
            saved_calls.append((k, v, ex))

        r.set = fake_set
        r.aclose = AsyncMock()

        cb = _make_cb()
        with patch("redis.asyncio.from_url", return_value=r):
            await cb.record_failure()

        assert len(saved_calls) == 1
        key, _, ttl = saved_calls[0]
        assert key == _REDIS_KEY
        assert ttl == _REDIS_TTL


# ── Redis failure fallback to in-memory state ─────────────────────────────────


class TestRedisFallback:
    async def test_redis_failure_falls_back_to_in_memory(self):
        """When Redis raises, the CB uses its in-memory copy."""
        cb = _make_cb()
        # Manually set in-memory state to OPEN
        cb._mem = {
            "state": OPEN,
            "failure_count": 3,
            "last_failure_time": time.time(),
            "last_state_change": time.time(),
        }

        with patch("redis.asyncio.from_url", side_effect=ConnectionError("redis down")):
            result = await cb.allow_request()

        assert result is False

    async def test_redis_write_failure_does_not_raise(self):
        """If Redis.set raises, _save silently continues (in-memory updated)."""
        r = AsyncMock()
        r.get = AsyncMock(return_value=None)
        r.set = AsyncMock(side_effect=ConnectionError("redis down"))
        r.aclose = AsyncMock()

        cb = _make_cb()
        with patch("redis.asyncio.from_url", return_value=r):
            await cb.record_failure()  # should not raise

        # In-memory should reflect the failure
        assert cb._mem["failure_count"] == 1

    async def test_in_memory_state_updated_even_if_redis_unavailable(self):
        """record_failure() updates _mem regardless of Redis availability."""
        cb = _make_cb()

        with patch("redis.asyncio.from_url", side_effect=OSError("no redis")):
            await cb.record_failure()
            await cb.record_failure()
            await cb.record_failure()

        assert cb._mem["state"] == OPEN


# ── get_status ────────────────────────────────────────────────────────────────


class TestGetStatus:
    async def test_get_status_closed(self):
        cb = _make_cb()
        raw = _redis_state(state=CLOSED, failure_count=0)
        with patch("redis.asyncio.from_url", return_value=_mock_redis(raw)):
            status = await cb.get_status()

        assert status["circuit_state"] == CLOSED
        assert status["ai_gateway_healthy"] is True
        assert status["failure_count"] == 0
        assert status["last_failure"] is None

    async def test_get_status_open(self):
        cb = _make_cb()
        failure_ts = time.time() - 10
        raw = _redis_state(state=OPEN, failure_count=3, last_failure_time=failure_ts)
        with patch("redis.asyncio.from_url", return_value=_mock_redis(raw)):
            status = await cb.get_status()

        assert status["circuit_state"] == OPEN
        assert status["ai_gateway_healthy"] is False
        assert status["failure_count"] == 3
        assert status["last_failure"] is not None  # ISO timestamp string


# ── AIGatewayUnavailableError ─────────────────────────────────────────────────


class TestAIGatewayUnavailableError:
    def test_default_message(self):
        exc = AIGatewayUnavailableError()
        assert "temporarily unavailable" in str(exc)

    def test_custom_message(self):
        exc = AIGatewayUnavailableError("custom message")
        assert str(exc) == "custom message"

    def test_retry_after_default(self):
        exc = AIGatewayUnavailableError()
        assert exc.retry_after == 60

    def test_retry_after_custom(self):
        exc = AIGatewayUnavailableError(retry_after=120)
        assert exc.retry_after == 120

    def test_is_exception(self):
        assert isinstance(AIGatewayUnavailableError(), Exception)
