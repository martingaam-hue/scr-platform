"""Shared SQLAlchemy connection pool for Celery sync tasks.

Celery tasks run in separate processes and cannot use the async engine.
This module exposes a shared SYNC engine and session factory so that
worker processes don't create a new connection pool on every task invocation.
"""

from contextlib import contextmanager
from collections.abc import Generator

import structlog
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

logger = structlog.get_logger()

# Convert asyncpg URL to plain psycopg2 URL for synchronous use
_sync_url = (
    str(settings.DATABASE_URL_SYNC)
    .replace("postgresql+asyncpg://", "postgresql://")
    .replace("+asyncpg", "")
)

# Shared engine — created once per worker process, reused across all tasks.
# pool_size=5 is intentionally smaller than the async API pool (20) because
# Celery workers typically handle fewer concurrent tasks than ASGI.
_engine = create_engine(
    _sync_url,
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,        # Drop stale connections before reuse
    pool_recycle=1800,         # Recycle connections every 30 min
    connect_args={
        "options": (
            "-c statement_timeout=60000 "                   # 60s per statement
            "-c idle_in_transaction_session_timeout=120000" # 120s idle-in-tx
        )
    },
)

_SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False)


@contextmanager
def get_celery_db_session() -> Generator[Session, None, None]:
    """Context manager that yields a sync SQLAlchemy session.

    Commits on clean exit, rolls back on exception, and always closes.

    Usage::

        with get_celery_db_session() as session:
            project = session.get(Project, project_id)
    """
    session: Session = _SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
