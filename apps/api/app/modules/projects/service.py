"""Business logic for Projects module."""

import re
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant import tenant_filter
from app.models.dataroom import Document
from app.models.enums import (
    BudgetItemStatus,
    MilestoneStatus,
    ProjectStage,
    ProjectStatus,
    ProjectType,
)
from app.models.projects import Project, ProjectBudgetItem, ProjectMilestone, SignalScore
from app.schemas.auth import CurrentUser


# ── Helpers ─────────────────────────────────────────────────────────────────


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:500]


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


async def get_latest_signal_score(
    db: AsyncSession, project_id: uuid.UUID
) -> SignalScore | None:
    stmt = (
        select(SignalScore)
        .where(SignalScore.project_id == project_id)
        .order_by(SignalScore.version.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── Project CRUD ────────────────────────────────────────────────────────────


async def list_projects(
    db: AsyncSession,
    org_id: uuid.UUID,
    *,
    status: ProjectStatus | None = None,
    project_type: ProjectType | None = None,
    stage: ProjectStage | None = None,
    geography: str | None = None,
    score_min: int | None = None,
    score_max: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> tuple[list[Project], int]:
    base = select(Project).where(Project.is_deleted.is_(False))
    base = tenant_filter(base, org_id, Project)

    if status:
        base = base.where(Project.status == status)
    if project_type:
        base = base.where(Project.project_type == project_type)
    if stage:
        base = base.where(Project.stage == stage)
    if geography:
        base = base.where(Project.geography_country.ilike(f"%{geography}%"))
    if search:
        base = base.where(Project.name.ilike(f"%{search}%"))

    # Signal score filtering via subquery
    if score_min is not None or score_max is not None:
        latest_score = (
            select(
                SignalScore.project_id,
                func.max(SignalScore.version).label("max_ver"),
            )
            .group_by(SignalScore.project_id)
            .subquery()
        )
        score_sub = (
            select(SignalScore.project_id, SignalScore.overall_score)
            .join(
                latest_score,
                (SignalScore.project_id == latest_score.c.project_id)
                & (SignalScore.version == latest_score.c.max_ver),
            )
            .subquery()
        )
        base = base.join(
            score_sub, Project.id == score_sub.c.project_id, isouter=True
        )
        if score_min is not None:
            base = base.where(score_sub.c.overall_score >= score_min)
        if score_max is not None:
            base = base.where(score_sub.c.overall_score <= score_max)

    # Count
    count_stmt = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Sort
    sort_col = getattr(Project, sort_by, Project.created_at)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()
    base = base.order_by(order)

    # Paginate
    base = base.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(base)
    return list(result.scalars().all()), total


async def get_project(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> Project:
    return await _get_project_or_raise(db, project_id, org_id)


async def create_project(
    db: AsyncSession,
    current_user: CurrentUser,
    *,
    name: str,
    project_type: ProjectType,
    description: str = "",
    geography_country: str,
    geography_region: str = "",
    geography_coordinates: dict | None = None,
    technology_details: dict | None = None,
    capacity_mw: Decimal | None = None,
    total_investment_required: Decimal,
    currency: str = "USD",
    target_close_date=None,
    stage: ProjectStage = ProjectStage.CONCEPT,
    status: ProjectStatus = ProjectStatus.DRAFT,
) -> Project:
    slug = _slugify(name)
    # Ensure unique slug within org
    existing = await db.execute(
        select(func.count())
        .select_from(Project)
        .where(Project.org_id == current_user.org_id, Project.slug.like(f"{slug}%"))
    )
    count = existing.scalar_one()
    if count > 0:
        slug = f"{slug}-{count + 1}"

    project = Project(
        org_id=current_user.org_id,
        name=name,
        slug=slug,
        description=description,
        project_type=project_type,
        status=status,
        stage=stage,
        geography_country=geography_country,
        geography_region=geography_region,
        geography_coordinates=geography_coordinates,
        technology_details=technology_details,
        capacity_mw=capacity_mw,
        total_investment_required=total_investment_required,
        currency=currency,
        target_close_date=target_close_date,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    await db.commit()
    return project


async def update_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    **kwargs,
) -> Project:
    project = await _get_project_or_raise(db, project_id, org_id)
    for key, value in kwargs.items():
        if value is not None and hasattr(project, key):
            setattr(project, key, value)
    await db.flush()
    await db.refresh(project)
    await db.commit()
    return project


async def delete_project(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> None:
    project = await _get_project_or_raise(db, project_id, org_id)
    project.is_deleted = True
    await db.flush()
    await db.commit()


async def publish_project(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> Project:
    project = await _get_project_or_raise(db, project_id, org_id)

    # Validate completeness
    errors = []
    if not project.name:
        errors.append("name is required")
    if not project.description:
        errors.append("description is required")
    if not project.geography_country:
        errors.append("geography_country is required")
    if not project.total_investment_required:
        errors.append("total_investment_required is required")
    if errors:
        raise ValueError(f"Cannot publish: {', '.join(errors)}")

    project.is_published = True
    project.published_at = datetime.utcnow()
    if project.status == ProjectStatus.DRAFT:
        project.status = ProjectStatus.ACTIVE
    await db.flush()
    await db.refresh(project)
    await db.commit()
    return project


async def get_project_stats(
    db: AsyncSession, org_id: uuid.UUID
) -> dict:
    base = select(Project).where(
        Project.is_deleted.is_(False), Project.org_id == org_id
    )

    # Total projects
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    # Active fundraising
    fundraising = (
        await db.execute(
            select(func.count())
            .select_from(Project)
            .where(
                Project.org_id == org_id,
                Project.is_deleted.is_(False),
                Project.status == ProjectStatus.FUNDRAISING,
            )
        )
    ).scalar_one()

    # Total funding needed
    funding = (
        await db.execute(
            select(func.coalesce(func.sum(Project.total_investment_required), 0))
            .where(
                Project.org_id == org_id,
                Project.is_deleted.is_(False),
            )
        )
    ).scalar_one()

    # Avg signal score (latest per project)
    latest_scores_sub = (
        select(
            SignalScore.project_id,
            func.max(SignalScore.version).label("max_ver"),
        )
        .join(Project, SignalScore.project_id == Project.id)
        .where(Project.org_id == org_id, Project.is_deleted.is_(False))
        .group_by(SignalScore.project_id)
        .subquery()
    )
    avg_score_result = await db.execute(
        select(func.avg(SignalScore.overall_score))
        .join(
            latest_scores_sub,
            (SignalScore.project_id == latest_scores_sub.c.project_id)
            & (SignalScore.version == latest_scores_sub.c.max_ver),
        )
    )
    avg_score = avg_score_result.scalar_one()

    return {
        "total_projects": total,
        "active_fundraising": fundraising,
        "total_funding_needed": funding,
        "avg_signal_score": round(float(avg_score), 1) if avg_score else None,
    }


# ── Milestone CRUD ──────────────────────────────────────────────────────────


async def list_milestones(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> list[ProjectMilestone]:
    # Verify project belongs to org
    await _get_project_or_raise(db, project_id, org_id)
    stmt = (
        select(ProjectMilestone)
        .where(
            ProjectMilestone.project_id == project_id,
            ProjectMilestone.is_deleted.is_(False),
        )
        .order_by(ProjectMilestone.order_index.asc(), ProjectMilestone.target_date.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_milestone(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    *,
    name: str,
    description: str = "",
    target_date,
    order_index: int = 0,
) -> ProjectMilestone:
    await _get_project_or_raise(db, project_id, org_id)
    milestone = ProjectMilestone(
        project_id=project_id,
        name=name,
        description=description,
        target_date=target_date,
        order_index=order_index,
    )
    db.add(milestone)
    await db.flush()
    await db.refresh(milestone)
    await db.commit()
    return milestone


async def update_milestone(
    db: AsyncSession,
    milestone_id: uuid.UUID,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    **kwargs,
) -> ProjectMilestone:
    await _get_project_or_raise(db, project_id, org_id)
    stmt = select(ProjectMilestone).where(
        ProjectMilestone.id == milestone_id,
        ProjectMilestone.project_id == project_id,
        ProjectMilestone.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise LookupError(f"Milestone {milestone_id} not found")

    for key, value in kwargs.items():
        if value is not None and hasattr(milestone, key):
            setattr(milestone, key, value)

    # Auto-complete if status set to COMPLETED
    if kwargs.get("status") == MilestoneStatus.COMPLETED and not milestone.completed_date:
        from datetime import date as date_type
        milestone.completed_date = date_type.today()
        milestone.completion_pct = 100

    await db.flush()
    await db.refresh(milestone)
    await db.commit()
    return milestone


async def delete_milestone(
    db: AsyncSession,
    milestone_id: uuid.UUID,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    await _get_project_or_raise(db, project_id, org_id)
    stmt = select(ProjectMilestone).where(
        ProjectMilestone.id == milestone_id,
        ProjectMilestone.project_id == project_id,
        ProjectMilestone.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise LookupError(f"Milestone {milestone_id} not found")
    milestone.is_deleted = True
    await db.flush()
    await db.commit()


# ── Budget CRUD ─────────────────────────────────────────────────────────────


async def list_budget_items(
    db: AsyncSession, project_id: uuid.UUID, org_id: uuid.UUID
) -> list[ProjectBudgetItem]:
    await _get_project_or_raise(db, project_id, org_id)
    stmt = (
        select(ProjectBudgetItem)
        .where(
            ProjectBudgetItem.project_id == project_id,
            ProjectBudgetItem.is_deleted.is_(False),
        )
        .order_by(ProjectBudgetItem.category.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_budget_item(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    *,
    category: str,
    description: str = "",
    estimated_amount: Decimal,
    currency: str = "USD",
) -> ProjectBudgetItem:
    await _get_project_or_raise(db, project_id, org_id)
    item = ProjectBudgetItem(
        project_id=project_id,
        category=category,
        description=description,
        estimated_amount=estimated_amount,
        currency=currency,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    await db.commit()
    return item


async def update_budget_item(
    db: AsyncSession,
    budget_id: uuid.UUID,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    **kwargs,
) -> ProjectBudgetItem:
    await _get_project_or_raise(db, project_id, org_id)
    stmt = select(ProjectBudgetItem).where(
        ProjectBudgetItem.id == budget_id,
        ProjectBudgetItem.project_id == project_id,
        ProjectBudgetItem.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise LookupError(f"Budget item {budget_id} not found")

    for key, value in kwargs.items():
        if value is not None and hasattr(item, key):
            setattr(item, key, value)
    await db.flush()
    await db.refresh(item)
    await db.commit()
    return item


async def delete_budget_item(
    db: AsyncSession,
    budget_id: uuid.UUID,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> None:
    await _get_project_or_raise(db, project_id, org_id)
    stmt = select(ProjectBudgetItem).where(
        ProjectBudgetItem.id == budget_id,
        ProjectBudgetItem.project_id == project_id,
        ProjectBudgetItem.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise LookupError(f"Budget item {budget_id} not found")
    item.is_deleted = True
    await db.flush()
    await db.commit()


# ── Business Plan AI ──────────────────────────────────────────────────────────


async def create_business_plan_task(
    db: AsyncSession,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    action_type: str,
) -> "AITaskLog":  # type: ignore[name-defined]
    """Create an AITaskLog and enqueue the business plan Celery task."""
    from app.models.ai import AITaskLog
    from app.models.enums import AIAgentType, AITaskStatus
    from app.modules.projects.tasks import business_plan_task

    await _get_project_or_raise(db, project_id, org_id)

    task_log = AITaskLog(
        org_id=org_id,
        user_id=user_id,
        agent_type=AIAgentType.REPORT,
        entity_type="project",
        entity_id=project_id,
        status=AITaskStatus.PENDING,
        input_data={"action_type": action_type},
    )
    db.add(task_log)
    await db.flush()
    await db.refresh(task_log)
    await db.commit()

    business_plan_task.delay(
        str(project_id),
        str(org_id),
        str(task_log.id),
        action_type,
    )
    return task_log


async def get_business_plan_result(
    db: AsyncSession,
    task_log_id: uuid.UUID,
    project_id: uuid.UUID,
    org_id: uuid.UUID,
) -> dict | None:
    from app.models.ai import AITaskLog
    from app.modules.projects.schemas import BusinessPlanResultResponse

    stmt = select(AITaskLog).where(
        AITaskLog.id == task_log_id,
        AITaskLog.entity_id == project_id,
        AITaskLog.org_id == org_id,
    )
    result = await db.execute(stmt)
    task_log = result.scalar_one_or_none()
    if not task_log:
        return None

    output = task_log.output_data or {}
    return BusinessPlanResultResponse(
        task_log_id=task_log.id,
        action_type=output.get("action_type", (task_log.input_data or {}).get("action_type", "")),
        status=task_log.status.value,
        content=output.get("content"),
        model_used=task_log.model_used,
        created_at=task_log.created_at,
    )
