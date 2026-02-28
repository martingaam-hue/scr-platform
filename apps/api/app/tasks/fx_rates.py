"""Celery task — fetch ECB FX reference rates daily at 3pm UTC."""

from __future__ import annotations

import asyncio

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(name="tasks.fetch_daily_fx_rates", bind=True, max_retries=3, default_retry_delay=300)
def fetch_daily_fx_rates(self) -> dict:
    """Fetch ECB daily reference rates and store them in the DB.

    Scheduled by Celery Beat at 15:00 UTC (4pm CET / 3pm UTC in winter).
    """
    from app.core.database import AsyncSessionLocal
    from app.modules.fx.service import fetch_ecb_rates

    async def _run() -> dict:
        async with AsyncSessionLocal() as db:
            try:
                rates = await fetch_ecb_rates(db)
                logger.info("fx_task.complete", currencies=len(rates))
                return {"status": "ok", "currencies_fetched": len(rates)}
            except Exception as exc:
                logger.error("fx_task.failed", error=str(exc))
                raise

    try:
        return asyncio.get_event_loop().run_until_complete(_run())
    except Exception as exc:
        raise self.retry(exc=exc)
