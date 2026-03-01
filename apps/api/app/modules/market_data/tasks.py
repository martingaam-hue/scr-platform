"""Market Data Celery tasks — fetch public economic indicators daily."""

from __future__ import annotations

import asyncio

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(name="tasks.fetch_market_data", bind=True, max_retries=3)
def fetch_market_data_task(self) -> dict:  # type: ignore[type-arg]
    """Fetch FRED + World Bank data and upsert into external_data_points."""
    try:
        return asyncio.run(_run_ingestion())
    except Exception as exc:
        logger.error("market_data.task.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=60 * 5) from exc


async def _run_ingestion() -> dict:
    from app.core.database import async_session_factory
    from app.modules.market_data import service

    async with async_session_factory() as db:
        fred_rows = await service.ingest_fred_data(db)
        wb_rows = await service.ingest_worldbank_data(db)

    total = fred_rows + wb_rows
    logger.info("market_data.ingestion.complete", fred_rows=fred_rows, wb_rows=wb_rows, total=total)
    return {"fred_rows": fred_rows, "wb_rows": wb_rows, "total": total}
