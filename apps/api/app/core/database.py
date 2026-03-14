from decimal import Decimal
from typing import ClassVar

import structlog
from sqlalchemy import Numeric
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = structlog.get_logger()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Drop stale connections before use
    pool_recycle=1800,  # Recycle connections every 30 min (avoids server-side timeouts)
    pool_timeout=30,  # Wait max 30s for a pool connection before raising
    connect_args={
        "server_settings": {
            "statement_timeout": "30000",  # 30s max per SQL statement
            "idle_in_transaction_session_timeout": "60000",  # Kill idle-in-tx sessions after 60s
            "lock_timeout": "10000",  # 10s max waiting for a row lock
        },
        "command_timeout": 30,  # asyncpg network-level command timeout (seconds)
    },
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Read replica (optional) ───────────────────────────────────────────────────
# Falls back to primary when DATABASE_URL_READ_REPLICA is not set.

_read_replica_url = getattr(settings, "DATABASE_URL_READ_REPLICA", None)
if _read_replica_url:
    _read_engine = create_async_engine(
        _read_replica_url,
        echo=settings.APP_DEBUG,
        pool_size=15,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_timeout=30,
        connect_args={
            "server_settings": {
                "statement_timeout": "30000",
                "idle_in_transaction_session_timeout": "60000",
                "lock_timeout": "10000",
            },
            "command_timeout": 30,
        },
    )
    logger.info("read_replica_configured")
else:
    _read_engine = engine  # type: ignore[assignment]

read_only_session_factory = async_sessionmaker(
    _read_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Replica lag monitoring ────────────────────────────────────────────────────

_REPLICA_LAG_REDIS_KEY = "replica_lag_seconds"
_REPLICA_LAG_REDIS_TTL = 30  # seconds — cache TTL for lag value
_REPLICA_LAG_FAILOVER_THRESHOLD = 30.0  # seconds — route to primary above this


async def get_cached_replica_lag() -> float | None:
    """Return replica lag in seconds (Redis-cached, 30 s TTL).

    Returns ``None`` when:
    - No read replica is configured.
    - Both Redis and the replica are unreachable (fail-open).

    On a Redis cache-miss the lag is queried from the replica directly and
    written back to Redis so subsequent callers within the TTL window skip
    the SQL round-trip.
    """
    if _read_replica_url is None:
        return None

    try:
        import redis.asyncio as aioredis

        from app.core.config import settings

        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        raw = await r.get(_REPLICA_LAG_REDIS_KEY)
        await r.aclose()
        if raw is not None:
            return float(raw)
    except Exception:
        pass

    # Cache miss — query the replica directly
    try:
        from sqlalchemy import text

        async with read_only_session_factory() as session:
            result = await session.execute(
                text("SELECT EXTRACT(EPOCH FROM" " (now() - pg_last_xact_replay_timestamp()))")
            )
            lag = result.scalar()

        if lag is None:
            return None

        lag_f = float(lag)

        # Write back to Redis (best-effort)
        try:
            import redis.asyncio as aioredis

            from app.core.config import settings

            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await r.set(_REPLICA_LAG_REDIS_KEY, str(lag_f), ex=_REPLICA_LAG_REDIS_TTL)
            await r.aclose()
        except Exception:
            pass

        return lag_f
    except Exception:
        return None  # fail open — caller will use replica as normal


class Base(DeclarativeBase):
    type_annotation_map: ClassVar[dict] = {
        Decimal: Numeric(19, 4),
    }


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_readonly_db() -> AsyncSession:  # type: ignore[misc]
    """Read-only session — routed to replica if DATABASE_URL_READ_REPLICA is set.

    Automatically falls back to the primary when replica lag exceeds
    ``_REPLICA_LAG_FAILOVER_THRESHOLD`` seconds (cached in Redis for 30 s).
    Use for analytics, dashboards, and listing endpoints that don't need writes.
    """
    factory = read_only_session_factory
    if _read_replica_url:
        lag = await get_cached_replica_lag()
        if lag is not None and lag > _REPLICA_LAG_FAILOVER_THRESHOLD:
            logger.warning(
                "replica_lag_failover",
                lag_seconds=round(lag, 1),
                msg="Replica lag too high — routing read to primary",
            )
            factory = async_session_factory

    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_readonly_session() -> AsyncSession:  # type: ignore[misc]
    """Yields a read-only session — routes to read replica if configured.

    Automatically falls back to the primary when replica lag exceeds
    ``_REPLICA_LAG_FAILOVER_THRESHOLD`` seconds (cached in Redis for 30 s).
    Alias for get_readonly_db with the naming convention used by replica-routed routers.
    """
    factory = read_only_session_factory
    if _read_replica_url:
        lag = await get_cached_replica_lag()
        if lag is not None and lag > _REPLICA_LAG_FAILOVER_THRESHOLD:
            logger.warning(
                "replica_lag_failover",
                lag_seconds=round(lag, 1),
                msg="Replica lag too high — routing read to primary",
            )
            factory = async_session_factory

    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()
