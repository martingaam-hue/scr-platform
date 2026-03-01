"""Celery tasks for async Signal Score calculation."""

import uuid
from datetime import datetime, timezone

import structlog
from celery import Celery

from app.core.config import settings

logger = structlog.get_logger()

celery_app = Celery("signal_score", broker=settings.CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def calculate_signal_score_task(
    self,
    project_id: str,
    org_id: str,
    user_id: str,
    task_log_id: str,
) -> dict:
    """Run Signal Score calculation pipeline.

    Steps:
      1. Update AITaskLog → PROCESSING
      2. Run SignalScoreEngine.calculate_score()
      3. Update AITaskLog → COMPLETED (or FAILED on error)
    """
    import time

    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession

    from app.models.ai import AITaskLog
    from app.models.enums import AITaskStatus
    from app.modules.signal_score.engine import SignalScoreEngine

    engine = create_engine(settings.DATABASE_URL_SYNC)
    task_log_uuid = uuid.UUID(task_log_id)
    start_time = time.time()

    with SyncSession(engine) as session:
        task_log = session.get(AITaskLog, task_log_uuid)
        if not task_log:
            logger.error("task_log_not_found", task_log_id=task_log_id)
            return {"status": "error", "detail": "Task log not found"}

        try:
            # Step 1: Update status
            task_log.status = AITaskStatus.PROCESSING
            session.commit()

            # Step 2: Run scoring engine
            scoring_engine = SignalScoreEngine(session)
            signal_score = scoring_engine.calculate_score(
                uuid.UUID(project_id),
                uuid.UUID(org_id),
                uuid.UUID(user_id),
            )

            # Step 3: Update task log
            elapsed_ms = int((time.time() - start_time) * 1000)
            task_log.status = AITaskStatus.COMPLETED
            task_log.output_data = {
                "signal_score_id": str(signal_score.id),
                "overall_score": signal_score.overall_score,
                "version": signal_score.version,
            }
            task_log.model_used = signal_score.model_used
            task_log.processing_time_ms = elapsed_ms
            session.commit()

            # Record metric snapshot
            try:
                from app.modules.metrics.snapshot_service import MetricSnapshotService
                from app.core.database import async_session_factory

                async def _record_snapshot() -> None:
                    async with async_session_factory() as async_db:
                        svc = MetricSnapshotService(async_db)
                        await svc.record_snapshot(
                            org_id=uuid.UUID(org_id),
                            entity_type="project",
                            entity_id=uuid.UUID(project_id),
                            metric_name="signal_score",
                            value=float(signal_score.overall_score),
                            metadata={
                                "dimensions": {
                                    "project_viability": signal_score.project_viability_score,
                                    "financial_planning": signal_score.financial_planning_score,
                                    "team_strength": signal_score.team_strength_score,
                                    "risk_assessment": signal_score.risk_assessment_score,
                                    "esg": signal_score.esg_score,
                                },
                                "version": signal_score.version,
                            },
                            trigger_event="score_calculated",
                            trigger_entity_id=task_log_uuid,
                        )
                        await async_db.commit()

                asyncio.run(_record_snapshot())
            except Exception as e:
                logger.warning("signal_score_snapshot_failed", error=str(e))

            # Evaluate certification after score update
            try:
                from app.modules.certification import service as cert_service
                from app.core.database import async_session_factory
                import asyncio

                async def _run_cert_eval() -> None:
                    async with async_session_factory() as async_db:
                        await cert_service.evaluate_certification(
                            async_db,
                            uuid.UUID(project_id),
                            uuid.UUID(org_id),
                        )

                asyncio.run(_run_cert_eval())
            except Exception as e:
                logger.warning("certification_evaluation_failed", error=str(e))

            # Award gamification badges after score update
            try:
                from app.modules.gamification import service as gamification_service
                from app.core.database import async_session_factory
                import asyncio

                async def _run_badge_eval() -> None:
                    async with async_session_factory() as async_db:
                        await gamification_service.evaluate_badges(
                            async_db,
                            uuid.UUID(user_id),
                            uuid.UUID(project_id),
                            "signal_score_computed",
                        )
                        await gamification_service.generate_quests(
                            async_db,
                            uuid.UUID(project_id),
                        )

                asyncio.run(_run_badge_eval())
            except Exception as e:
                logger.warning("gamification_evaluation_failed", error=str(e))

            logger.info(
                "signal_score_task_completed",
                project_id=project_id,
                overall_score=signal_score.overall_score,
                version=signal_score.version,
                elapsed_ms=elapsed_ms,
            )
            return {
                "status": "success",
                "signal_score_id": str(signal_score.id),
                "overall_score": signal_score.overall_score,
            }

        except Exception as exc:
            session.rollback()
            # Update error status in fresh session
            with SyncSession(engine) as err_session:
                err_log = err_session.get(AITaskLog, task_log_uuid)
                if err_log:
                    err_log.status = AITaskStatus.FAILED
                    err_log.error_message = str(exc)[:1000]
                    err_log.processing_time_ms = int(
                        (time.time() - start_time) * 1000
                    )
                    err_session.commit()

            logger.error(
                "signal_score_task_failed",
                project_id=project_id,
                task_log_id=task_log_id,
                error=str(exc),
            )
            raise self.retry(exc=exc)
