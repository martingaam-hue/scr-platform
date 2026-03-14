"""Blockchain anchor batch-submission Celery task — runs nightly at 02:00 UTC.

The task collects all pending BlockchainAnchor records, builds a Merkle tree,
and submits the root to Polygon in a single transaction.  All Web3 calls are
executed inside run_in_executor() in the service layer, so the event loop is
never blocked.
"""

from __future__ import annotations

import asyncio

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(
    name="app.tasks.blockchain.submit_audit_batch",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 min between retries
)
def submit_audit_batch(self) -> dict:  # type: ignore[type-arg]
    """Batch pending blockchain anchors into a Merkle tree and submit to Polygon.

    Scheduled nightly at 02:00 UTC via Celery Beat (see worker.py).
    Retries up to 3 times on transient failures with a 5-minute delay.
    """
    from app.core.database import async_session_factory
    from app.modules.blockchain_audit.service import batch_submit

    async def _run() -> dict:  # type: ignore[type-arg]
        async with async_session_factory() as db:
            result = await batch_submit(db)
        logger.info("blockchain.batch_complete", **result)
        return result

    try:
        result = asyncio.run(_run())
        logger.info(
            "blockchain.task_complete",
            status=result.get("status"),
            count=result.get("count", 0),
            tx_hash=result.get("tx_hash"),
        )
        return result
    except Exception as exc:
        logger.error("blockchain.task_failed", error=str(exc), retries=self.request.retries)
        raise self.retry(exc=exc) from exc


# Backward-compatible alias — the old 6-hourly task name still works
batch_blockchain_anchors = submit_audit_batch
