from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

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
