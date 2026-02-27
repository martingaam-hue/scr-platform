"""Celery tasks for async Business Plan AI generation."""

import uuid

import structlog
from celery import Celery

from app.core.config import settings

logger = structlog.get_logger()

celery_app = Celery("projects", broker=settings.CELERY_BROKER_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

ACTION_PROMPTS = {
    "executive_summary": (
        "Write a polished 2-3 paragraph executive summary for an impact investment project. "
        "Highlight the mission, scale, and investment opportunity. Tone: professional, compelling."
    ),
    "financial_overview": (
        "Write a 2-paragraph financial projections overview. Describe the expected returns, "
        "revenue model, and financial milestones. Tone: analytical, investor-focused."
    ),
    "market_analysis": (
        "Write a 2-3 paragraph market and competitive analysis. Cover market size, growth trends, "
        "competitive landscape, and the project's positioning. Tone: insightful, data-driven."
    ),
    "risk_narrative": (
        "Write a structured risk assessment narrative. Identify the top 3-4 risks (technical, "
        "financial, regulatory, market) and describe concrete mitigation strategies for each. "
        "Tone: measured, reassuring."
    ),
    "esg_statement": (
        "Write a 2-paragraph ESG and impact statement. Cover environmental benefits, social impact, "
        "governance approach, and alignment with UN SDGs. Tone: impactful, authentic."
    ),
    "technical_summary": (
        "Write a 1-2 paragraph technical feasibility summary. Describe the technology, capacity, "
        "implementation approach, and key technical risks. Tone: clear, credible."
    ),
    "investor_pitch": (
        "Write a compelling 150-word elevator pitch for investor conversations. Lead with the "
        "problem, describe the solution and impact, and close with the investment opportunity. "
        "Tone: energetic, persuasive."
    ),
}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def business_plan_task(
    self,
    project_id: str,
    org_id: str,
    task_log_id: str,
    action_type: str,
) -> dict:
    """Generate business plan content using AI Gateway."""
    import time

    import httpx
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as SyncSession

    from app.models.ai import AITaskLog
    from app.models.enums import AITaskStatus
    from app.models.projects import Project

    engine = create_engine(settings.DATABASE_URL_SYNC)
    task_log_uuid = uuid.UUID(task_log_id)
    start_time = time.time()

    with SyncSession(engine) as session:
        task_log = session.get(AITaskLog, task_log_uuid)
        if not task_log:
            return {"status": "error", "detail": "Task log not found"}

        try:
            task_log.status = AITaskStatus.PROCESSING
            session.commit()

            # Load project
            project = session.get(Project, uuid.UUID(project_id))
            if not project:
                raise LookupError(f"Project {project_id} not found")

            action_prompt = ACTION_PROMPTS.get(action_type, "Describe this project.")

            system_prompt = (
                f"You are a professional investment writer specialising in impact finance. "
                f"{action_prompt}"
            )
            user_prompt = (
                f"Project: {project.name}\n"
                f"Type: {project.project_type.value}\n"
                f"Stage: {project.stage.value}\n"
                f"Country: {project.geography_country}\n"
                f"Investment Required: {project.total_investment_required} {project.currency}\n"
                f"Capacity: {project.capacity_mw} MW\n"
                f"Description: {(project.description or '')[:1500]}\n\n"
                f"Write the requested content now."
            )

            response = httpx.post(
                f"{settings.AI_GATEWAY_URL}/v1/completions",
                json={
                    "task_type": "analysis",
                    "system": system_prompt,
                    "prompt": user_prompt,
                    "max_tokens": 800,
                    "temperature": 0.6,
                },
                headers={"Authorization": f"Bearer {settings.AI_GATEWAY_API_KEY}"},
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
            content = data.get("content") or data.get("text") or ""
            model_used = data.get("model", "claude-sonnet-4")

            elapsed_ms = int((time.time() - start_time) * 1000)
            task_log.status = AITaskStatus.COMPLETED
            task_log.output_data = {
                "action_type": action_type,
                "content": content,
            }
            task_log.model_used = model_used
            task_log.processing_time_ms = elapsed_ms
            session.commit()

            logger.info(
                "business_plan_task_completed",
                project_id=project_id,
                action_type=action_type,
                elapsed_ms=elapsed_ms,
            )
            return {"status": "success", "action_type": action_type}

        except Exception as exc:
            session.rollback()
            with SyncSession(engine) as err_session:
                err_log = err_session.get(AITaskLog, task_log_uuid)
                if err_log:
                    err_log.status = AITaskStatus.FAILED
                    err_log.error_message = str(exc)[:1000]
                    err_session.commit()

            logger.error(
                "business_plan_task_failed",
                project_id=project_id,
                action_type=action_type,
                error=str(exc),
            )
            raise self.retry(exc=exc)
