"""Async service layer for Signal Score operations."""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant import tenant_filter
from app.models.ai import AITaskLog
from app.models.enums import AIAgentType, AITaskStatus
from app.models.projects import Project, SignalScore

logger = structlog.get_logger()


async def _get_project_or_raise(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> Project:
    stmt = select(Project).where(
        Project.id == project_id, Project.is_deleted.is_(False)
    )
    stmt = tenant_filter(stmt, org_id, Project)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()
    if not project:
        raise LookupError(f"Project {project_id} not found")
    return project


async def trigger_calculation(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> AITaskLog:
    """Create AITaskLog and dispatch Celery task."""
    # Verify project exists and belongs to org
    await _get_project_or_raise(db, project_id, org_id)

    # Create task log
    task_log = AITaskLog(
        org_id=org_id,
        agent_type=AIAgentType.SCORING,
        entity_type="project",
        entity_id=project_id,
        status=AITaskStatus.PENDING,
        input_data={"project_id": str(project_id)},
        triggered_by=user_id,
    )
    db.add(task_log)
    await db.flush()

    # Dispatch Celery task
    from app.modules.signal_score.tasks import calculate_signal_score_task

    calculate_signal_score_task.delay(
        str(project_id), str(org_id), str(user_id), str(task_log.id)
    )

    logger.info(
        "signal_score_calculation_triggered",
        project_id=str(project_id),
        task_log_id=str(task_log.id),
    )
    return task_log


async def get_latest_score(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> SignalScore | None:
    """Get most recent signal score for a project."""
    # Verify project belongs to org
    await _get_project_or_raise(db, project_id, org_id)

    stmt = (
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_score_history(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> list[SignalScore]:
    """Get all signal scores ordered by version desc."""
    await _get_project_or_raise(db, project_id, org_id)

    stmt = (
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_live_score(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> dict:
    """Synchronous quick score from project metadata completeness only.

    No AI calls, no document analysis. Returns immediately.
    """
    project = await _get_project_or_raise(db, project_id, org_id)

    factors = []
    score = 0

    def _add(name: str, met: bool, impact: int) -> None:
        if met:
            score_inc = impact
        else:
            score_inc = 0
        nonlocal score
        score += score_inc
        factors.append({"name": name, "met": met, "impact": impact})

    desc = project.description or ""
    if len(desc) >= 300:
        _add("Detailed project description (300+ chars)", True, 15)
    elif len(desc) >= 50:
        _add("Basic project description", True, 8)
    else:
        _add("Project description", False, 15)

    _add("Project stage defined", bool(project.stage), 10)
    _add("Geography set", bool(project.geography_country), 10)
    _add(
        "Investment target set",
        bool(project.total_investment_required)
        and float(project.total_investment_required or 0) > 0,
        15,
    )
    _add("Asset type defined", bool(project.project_type), 10)
    _add("Project published", bool(project.is_published), 10)
    _add("Cover image added", bool(project.cover_image_url), 5)
    _add("Target close date set", bool(project.target_close_date), 10)
    _add("Capacity specified", bool(project.capacity_mw), 10)

    # Normalize: max reachable = 95 (description full = 15, rest = 80)
    overall = min(100, round(score * 100 / 95))

    missing = [f["name"] for f in factors if not f["met"]]
    if missing:
        guidance = f"Complete these fields to improve your quick score: {', '.join(missing[:3])}."
    else:
        guidance = "Excellent metadata completeness. Run a full signal score to unlock AI-powered analysis."

    return {"overall_score": overall, "factors": factors, "guidance": guidance}


async def get_task_status(
    db: AsyncSession, task_log_id: uuid.UUID, org_id: uuid.UUID
) -> AITaskLog | None:
    """Check calculation task status."""
    stmt = select(AITaskLog).where(
        AITaskLog.id == task_log_id,
        AITaskLog.org_id == org_id,
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
