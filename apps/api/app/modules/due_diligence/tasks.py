"""Celery tasks for Due Diligence AI review."""

from __future__ import annotations

import asyncio
import uuid

import structlog

from app.core.config import settings
from celery import Celery

logger = structlog.get_logger()

_celery = Celery("dd_tasks", broker=settings.CELERY_BROKER_URL)
_celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


async def _async_review(
    item_status_id: str,
    document_id: str,
    criteria: str,
) -> None:
    """Async inner function for AI review of a document against a DD checklist item."""
    import httpx
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session as SyncSession

    from app.models.dataroom import Document, DocumentExtraction
    from app.models.due_diligence import DDItemStatus, DDProjectChecklist

    engine = create_engine(settings.DATABASE_URL_SYNC)
    item_status_uuid = uuid.UUID(item_status_id)
    document_uuid = uuid.UUID(document_id)

    with SyncSession(engine) as session:
        # 1. Load document
        document = session.get(Document, document_uuid)
        if not document:
            logger.error("dd_review.document_not_found", document_id=document_id)
            return

        # 2. Load extraction text
        extraction_stmt = (
            select(DocumentExtraction)
            .where(DocumentExtraction.document_id == document_uuid)
            .order_by(DocumentExtraction.created_at.desc())
            .limit(1)
        )
        extraction_result = session.execute(extraction_stmt)
        extraction = extraction_result.scalar_one_or_none()

        document_text = ""
        if extraction and extraction.result:
            # Try to get text content from extraction result
            result_data = extraction.result
            if isinstance(result_data, dict):
                document_text = (
                    result_data.get("content")
                    or result_data.get("text")
                    or result_data.get("summary")
                    or str(result_data)
                )
            else:
                document_text = str(result_data)

        # Truncate to 8000 chars for AI prompt
        document_text = document_text[:8000]

        # 3. Call AI gateway
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{settings.AI_GATEWAY_URL}/v1/completions",
                    headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                    json={
                        "task_type": "dd_review_item",
                        "variables": {
                            "item_criteria": criteria,
                            "document_name": document.name,
                            "document_text": document_text or "(no extracted text available)",
                        },
                    },
                )
                resp.raise_for_status()
                response_data = resp.json()
        except Exception as exc:
            logger.error("dd_review.ai_call_failed", error=str(exc), item_status_id=item_status_id)
            # Mark as failed
            item_status = session.get(DDItemStatus, item_status_uuid)
            if item_status:
                item_status.status = "pending"
                item_status.ai_review_result = {"error": str(exc)}
                session.commit()
            return

        # 4. Parse AI response
        ai_result: dict = {}
        if response_data.get("data"):
            ai_result = response_data["data"]
        elif isinstance(response_data, dict):
            ai_result = response_data

        satisfied = ai_result.get("satisfied", False)
        confidence = float(ai_result.get("confidence", 0.0))

        # Determine new status
        if satisfied and confidence > 0.7:
            new_status = "satisfied"
        elif satisfied and confidence <= 0.7:
            new_status = "partially_met"
        else:
            new_status = "not_met"

        # 5. Update DDItemStatus
        from datetime import datetime, timezone
        item_status = session.get(DDItemStatus, item_status_uuid)
        if not item_status:
            logger.error("dd_review.item_status_not_found", item_status_id=item_status_id)
            return

        item_status.ai_review_result = ai_result
        item_status.status = new_status
        item_status.reviewed_at = datetime.now(timezone.utc)
        session.flush()

        # 6. Update completion percentage
        checklist = session.get(DDProjectChecklist, item_status.checklist_id)
        if checklist:
            all_statuses_stmt = select(DDItemStatus).where(
                DDItemStatus.checklist_id == checklist.id,
                DDItemStatus.is_deleted.is_(False),
            )
            all_statuses = session.execute(all_statuses_stmt).scalars().all()
            done_statuses = {"satisfied", "partially_met", "waived"}
            completed = sum(1 for s in all_statuses if s.status in done_statuses)
            total = len(all_statuses)
            checklist.completion_percentage = round((completed / total * 100) if total > 0 else 0.0, 1)
            checklist.completed_items = completed
            checklist.total_items = total
            if checklist.completion_percentage >= 100:
                checklist.status = "completed"

        session.commit()
        logger.info(
            "dd_review.complete",
            item_status_id=item_status_id,
            new_status=new_status,
            confidence=confidence,
        )


@_celery.task(name="tasks.review_dd_item", bind=True, max_retries=3)
def review_dd_item_task(self, item_status_id: str, document_id: str, criteria: str):
    """AI review of a document against a DD checklist item."""
    try:
        asyncio.get_event_loop().run_until_complete(
            _async_review(item_status_id, document_id, criteria)
        )
    except Exception as exc:
        logger.error("review_dd_item_task.failed", error=str(exc), item_status_id=item_status_id)
        raise self.retry(exc=exc, countdown=60) from exc
