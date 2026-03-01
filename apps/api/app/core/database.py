import structlog
from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = structlog.get_logger()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,               # Drop stale connections before use
    pool_recycle=1800,                 # Recycle connections every 30 min (avoids server-side timeouts)
    pool_timeout=30,                   # Wait max 30s for a pool connection before raising
    connect_args={
        "server_settings": {
            "statement_timeout": "30000",                    # 30s max per SQL statement
            "idle_in_transaction_session_timeout": "60000",  # Kill idle-in-tx sessions after 60s
            "lock_timeout": "10000",                         # 10s max waiting for a row lock
        },
        "command_timeout": 30,         # asyncpg network-level command timeout (seconds)
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


class Base(DeclarativeBase):
    type_annotation_map = {
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

    Use for analytics, dashboards, and listing endpoints that don't need writes.
    """
    async with read_only_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
