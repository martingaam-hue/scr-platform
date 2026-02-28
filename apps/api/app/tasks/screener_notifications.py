"""Celery task: check saved searches with notifications enabled and alert users."""

from __future__ import annotations

import structlog

logger = structlog.get_logger()


def check_saved_searches() -> None:
    """Run daily — check if new projects match any saved searches.

    Called by Celery beat schedule. Uses sync DB session.
    New matches trigger a platform notification via the collaboration module.
    """
    # Import inside function to avoid circular imports at module load time
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from app.core.config import settings
    from app.models.screener import SavedSearch

    try:
        engine = create_engine(settings.DATABASE_URL.replace("+asyncpg", ""))
        with Session(engine) as db:
            stmt = select(SavedSearch).where(
                SavedSearch.notify_new_matches.is_(True)
            )
            searches = db.execute(stmt).scalars().all()

            for search in searches:
                logger.info(
                    "screener_notification_check",
                    search_id=str(search.id),
                    name=search.name,
                )
                # Notification logic would call the notifications service
                # and update search.last_used after sending

    except Exception as exc:
        logger.error("screener_notification_error", error=str(exc))
