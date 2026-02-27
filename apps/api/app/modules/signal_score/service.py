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
