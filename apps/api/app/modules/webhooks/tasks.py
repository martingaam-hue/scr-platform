"""Celery tasks for webhook delivery and retry."""

from __future__ import annotations

import asyncio
import uuid

import structlog
from celery import shared_task

logger = structlog.get_logger()


@shared_task(name="tasks.deliver_webhook", bind=True, max_retries=0)
def deliver_webhook_task(self, delivery_id: str) -> dict:  # type: ignore[misc]
    """Deliver a single webhook event to the subscriber endpoint."""

    async def _run() -> bool:
        from app.core.database import async_session_factory
        from app.modules.webhooks.service import WebhookService

        async with async_session_factory() as db:
            svc = WebhookService(db)
            return await svc.deliver(uuid.UUID(delivery_id))

    result = asyncio.run(_run())
    logger.info("webhook_delivery_task_done", delivery_id=delivery_id, success=result)
    return {"delivery_id": delivery_id, "success": result}


@shared_task(name="tasks.retry_pending_webhooks")
def retry_pending_webhooks() -> dict:
    """Beat task: retry deliveries whose next_retry_at has passed."""

    async def _run() -> int:
        from datetime import datetime

        from sqlalchemy import select

        from app.core.database import async_session_factory
        from app.models.webhooks import WebhookDelivery

        async with async_session_factory() as db:
            stmt = select(WebhookDelivery).where(
                WebhookDelivery.status == "retrying",
                WebhookDelivery.next_retry_at <= datetime.utcnow(),
            )
            deliveries = (await db.execute(stmt)).scalars().all()
            count = len(deliveries)
            for d in deliveries:
                deliver_webhook_task.delay(str(d.id))
            return count

    count = asyncio.run(_run())
    logger.info("retry_pending_webhooks_queued", count=count)
    return {"queued": count}
