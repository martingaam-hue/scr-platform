"""Celery tasks for Expert Insights async enrichment."""

from __future__ import annotations

import asyncio
import uuid

import structlog

logger = structlog.get_logger()


def enrich_expert_note_task(note_id: str) -> None:
    """Fire-and-forget enrichment — runs in Celery worker via async_session_factory."""
    async def _run() -> None:
        from app.core.database import async_session_factory
        from app.modules.expert_insights.service import ExpertInsightsService

        async with async_session_factory() as db:
            svc = ExpertInsightsService(db)
            await svc.enrich_note(uuid.UUID(note_id))

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error("enrich_expert_note_task_failed", note_id=note_id, error=str(exc))


def enrich_expert_note_task_celery(note_id: str) -> None:
    """Celery-compatible wrapper — called by the shared_task below."""
    enrich_expert_note_task(note_id)


# Register with the main Celery worker if available
try:
    from app.worker import celery_app

    @celery_app.task(name="tasks.enrich_expert_note", bind=True, max_retries=3)  # type: ignore[misc]
    def _enrich_expert_note_celery(self, note_id: str) -> None:  # type: ignore[misc]
        try:
            enrich_expert_note_task(note_id)
        except Exception as exc:
            raise self.retry(exc=exc, countdown=60)

except Exception:
    # Worker module not importable in API context — that's fine.
    pass
