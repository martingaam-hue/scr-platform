"""Celery tasks for the AI Document Redaction module."""

from __future__ import annotations

import asyncio
import uuid

import structlog

logger = structlog.get_logger()


def _analyze_redaction_job(job_id: str, document_text: str) -> None:
    """Inner coroutine runner — safe to call from Celery or directly."""

    async def _run() -> None:
        from app.core.database import async_session_factory
        from app.modules.redaction.service import RedactionService

        async with async_session_factory() as db:
            svc = RedactionService(db)
            await svc.analyze_document(uuid.UUID(job_id), document_text)

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error("tasks.analyze_redaction_job.failed", job_id=job_id, error=str(exc))


def _apply_redaction(job_id: str) -> None:
    """Inner coroutine runner for the apply-redaction step."""

    async def _run() -> None:
        from app.core.database import async_session_factory
        from app.modules.redaction.service import RedactionService

        async with async_session_factory() as db:
            svc = RedactionService(db)
            await svc.generate_redacted_document(uuid.UUID(job_id))

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error("tasks.apply_redaction.failed", job_id=job_id, error=str(exc))


# Register with the main Celery worker if available
try:
    from app.worker import celery_app

    @celery_app.task(name="tasks.analyze_redaction_job", bind=True, max_retries=2)  # type: ignore[misc]
    def analyze_redaction_job_task(self, job_id: str, document_text: str) -> None:  # type: ignore[misc]
        try:
            _analyze_redaction_job(job_id, document_text)
        except Exception as exc:
            raise self.retry(exc=exc, countdown=30)

    @celery_app.task(name="tasks.apply_redaction", bind=True, max_retries=2)  # type: ignore[misc]
    def apply_redaction_task(self, job_id: str) -> None:  # type: ignore[misc]
        try:
            _apply_redaction(job_id)
        except Exception as exc:
            raise self.retry(exc=exc, countdown=30)

except Exception:
    # Worker module not importable in API context — define stubs for import safety.
    def analyze_redaction_job_task(job_id: str, document_text: str) -> None:  # type: ignore[misc]
        _analyze_redaction_job(job_id, document_text)

    def apply_redaction_task(job_id: str) -> None:  # type: ignore[misc]
        _apply_redaction(job_id)
