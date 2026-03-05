"""Watchlist monitoring Celery task — runs every 15 minutes."""

from __future__ import annotations

import asyncio

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(name="tasks.check_watchlists", bind=True, max_retries=3, default_retry_delay=120)
def check_watchlists(self) -> dict:
    """Check all active watchlists and create alerts for matches."""
    from app.core.database import async_session_factory
    from app.modules.watchlists.service import check_watchlist, get_active_watchlists

    async def _run() -> dict:
        total_alerts = 0
        async with async_session_factory() as db:
            watchlists = await get_active_watchlists(db)
            for wl in watchlists:
                try:
                    alerts = await check_watchlist(db, wl)
                    total_alerts += alerts
                except Exception as exc:
                    logger.error("watchlist.check_error", watchlist_id=str(wl.id), error=str(exc))
        logger.info("watchlists.checked", count=len(watchlists), alerts=total_alerts)
        return {
            "status": "ok",
            "watchlists_checked": len(watchlists),
            "alerts_created": total_alerts,
        }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc) from exc
