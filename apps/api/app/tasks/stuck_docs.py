"""Periodic Celery task: detect and fail documents/reports stuck in generating/processing states."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog
from celery import shared_task

logger = structlog.get_logger()

_STUCK_TIMEOUT_MINUTES = 10


@shared_task(name="tasks.cleanup_stuck_documents", soft_time_limit=60, time_limit=90)
def cleanup_stuck_documents() -> dict:
    """Find documents/reports stuck in generating/processing for >10 minutes and mark them failed.

    Runs every 5 minutes via Celery beat. Covers:
    - GeneratedReport (status=GENERATING)
    - AITaskLog (status=PROCESSING)
    - Dataroom Document (status=PROCESSING)
    - LegalDocument (metadata_.generation_status='generating')
    """
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session as SyncSession

    from app.core.config import settings

    engine = create_engine(settings.DATABASE_URL_SYNC)
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=_STUCK_TIMEOUT_MINUTES)
    total_fixed = 0

    with SyncSession(engine) as session:
        # ── 1. GeneratedReport stuck in GENERATING ──────────────────────────
        try:
            from app.models.enums import ReportStatus
            from app.models.reporting import GeneratedReport

            stuck_reports = session.execute(
                select(GeneratedReport).where(
                    GeneratedReport.status == ReportStatus.GENERATING,
                    GeneratedReport.created_at < cutoff,
                    GeneratedReport.is_deleted.is_(False),
                )
            ).scalars().all()

            for report in stuck_reports:
                report.status = ReportStatus.ERROR
                report.error_message = "Generation timed out"
                logger.warning(
                    "stuck_docs.report_timed_out",
                    report_id=str(report.id),
                    created_at=str(report.created_at),
                )
                total_fixed += 1

            if stuck_reports:
                session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("stuck_docs.report_cleanup_error", error=str(exc))

        # ── 2. AITaskLog stuck in PROCESSING ───────────────────────────────
        try:
            from app.models.ai import AITaskLog
            from app.models.enums import AITaskStatus

            stuck_tasks = session.execute(
                select(AITaskLog).where(
                    AITaskLog.status == AITaskStatus.PROCESSING,
                    AITaskLog.created_at < cutoff,
                )
            ).scalars().all()

            for task_log in stuck_tasks:
                task_log.status = AITaskStatus.FAILED
                task_log.error_message = "Generation timed out"
                logger.warning(
                    "stuck_docs.task_log_timed_out",
                    task_log_id=str(task_log.id),
                    agent_type=str(task_log.agent_type),
                    created_at=str(task_log.created_at),
                )
                total_fixed += 1

            if stuck_tasks:
                session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("stuck_docs.task_log_cleanup_error", error=str(exc))

        # ── 3. Dataroom Document stuck in PROCESSING ────────────────────────
        try:
            from app.models.dataroom import Document
            from app.models.enums import DocumentStatus

            stuck_docs = session.execute(
                select(Document).where(
                    Document.status == DocumentStatus.PROCESSING,
                    Document.created_at < cutoff,
                    Document.is_deleted.is_(False),
                )
            ).scalars().all()

            for doc in stuck_docs:
                doc.status = DocumentStatus.ERROR
                doc.metadata_ = {
                    **(doc.metadata_ or {}),
                    "processing_error": "Processing timed out",
                }
                logger.warning(
                    "stuck_docs.document_timed_out",
                    document_id=str(doc.id),
                    created_at=str(doc.created_at),
                )
                total_fixed += 1

            if stuck_docs:
                session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("stuck_docs.document_cleanup_error", error=str(exc))

        # ── 4. LegalDocument stuck in 'generating' (in metadata_ JSONB) ─────
        try:
            from app.models.legal import LegalDocument

            stuck_legal = session.execute(
                select(LegalDocument).where(
                    LegalDocument.metadata_["generation_status"].astext == "generating",
                    LegalDocument.created_at < cutoff,
                )
            ).scalars().all()

            for doc in stuck_legal:
                meta = dict(doc.metadata_ or {})
                meta["generation_status"] = "failed"
                meta["error"] = "Generation timed out"
                doc.metadata_ = meta
                logger.warning(
                    "stuck_docs.legal_doc_timed_out",
                    doc_id=str(doc.id),
                    created_at=str(doc.created_at),
                )
                total_fixed += 1

            if stuck_legal:
                session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("stuck_docs.legal_doc_cleanup_error", error=str(exc))

    if total_fixed > 0:
        logger.warning("stuck_docs.cleanup_complete", total_fixed=total_fixed)
    else:
        logger.info("stuck_docs.no_stuck_documents")

    return {"fixed": total_fixed}
