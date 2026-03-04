"""Alley signal_score Celery tasks — async score generation."""
from __future__ import annotations

import uuid

import structlog
from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SyncSession

logger = structlog.get_logger()


@shared_task(bind=True, max_retries=2, default_retry_delay=30, name="alley.signal_score.generate")
def run_signal_score_generation(self, task_log_id: str, org_id: str, project_id: str) -> None:
    """Generate a signal score for a project using uploaded context."""
    from app.core.config import settings
    from app.models.ai import AITaskLog
    from app.models.enums import AITaskStatus
    from app.models.projects import Project, SignalScore

    engine = create_engine(settings.DATABASE_URL_SYNC)

    with SyncSession(engine) as db:
        log = db.get(AITaskLog, uuid.UUID(task_log_id))
        if not log:
            logger.error("task_log_not_found", task_log_id=task_log_id)
            return
        log.status = AITaskStatus.RUNNING
        db.commit()

    try:
        import httpx

        with SyncSession(engine) as db:
            project = db.get(Project, uuid.UUID(project_id))
            if not project:
                raise ValueError(f"Project {project_id} not found")

            response = httpx.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "prompt": (
                        f"Generate an investment readiness signal score for project: {project.name}. "
                        "Return JSON with dimension scores (0-100) and gap analysis."
                    ),
                    "task_type": "signal_score",
                    "max_tokens": 2000,
                    "temperature": 0.2,
                },
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                timeout=120.0,
            )
            response.raise_for_status()
            ai_result = response.json()

            content = ai_result.get("content", {})
            if isinstance(content, str):
                import json as _json
                try:
                    content = _json.loads(content)
                except Exception:
                    content = {}

            from sqlalchemy import select as sa_select
            latest = db.execute(
                sa_select(SignalScore)
                .where(SignalScore.project_id == uuid.UUID(project_id))
                .order_by(SignalScore.version.desc())
                .limit(1)
            ).scalar_one_or_none()
            next_version = (latest.version + 1) if latest else 1

            new_score = SignalScore(
                project_id=uuid.UUID(project_id),
                org_id=uuid.UUID(org_id),
                version=next_version,
                overall_score=content.get("overall_score", 50),
                project_viability_score=content.get("project_viability_score", 50),
                financial_planning_score=content.get("financial_planning_score", 50),
                team_strength_score=content.get("team_strength_score", 50),
                risk_assessment_score=content.get("risk_assessment_score", 50),
                esg_score=content.get("esg_score", 50),
                market_opportunity_score=content.get("market_opportunity_score", 50),
                gaps=content.get("gaps", {}),
                strengths=content.get("strengths", {}),
                improvement_guidance=content.get("improvement_guidance", {}),
                score_factors=content.get("score_factors", {}),
                scoring_details=content.get("scoring_details", {}),
            )
            db.add(new_score)

            log = db.get(AITaskLog, uuid.UUID(task_log_id))
            if log:
                log.status = AITaskStatus.COMPLETED
                log.output_data = {
                    "signal_score_id": str(new_score.id),
                    "overall_score": new_score.overall_score,
                }
            db.commit()

    except Exception as exc:
        logger.error("signal_score_generation_failed", error=str(exc), task_log_id=task_log_id)
        with SyncSession(engine) as db:
            log = db.get(AITaskLog, uuid.UUID(task_log_id))
            if log:
                log.status = AITaskStatus.FAILED
                log.error_message = str(exc)
                db.commit()
        raise self.retry(exc=exc)
    finally:
        engine.dispose()
