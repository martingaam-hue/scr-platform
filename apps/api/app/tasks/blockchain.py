"""Blockchain anchor batch submission Celery task — runs every 6 hours."""

from __future__ import annotations

import asyncio

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(
    name="tasks.batch_blockchain_anchors", bind=True, max_retries=2, default_retry_delay=600
)
def batch_blockchain_anchors(self) -> dict:
    """Batch pending blockchain anchors into a Merkle tree and submit to Polygon."""
    from app.core.database import async_session_factory
    from app.modules.blockchain_audit.service import batch_submit

    async def _run() -> dict:
        async with async_session_factory() as db:
            result = await batch_submit(db)
        logger.info("blockchain.batch_complete", **result)
        return result

    try:
        return asyncio.run(_run())
    except Exception as exc:
        raise self.retry(exc=exc) from exc
