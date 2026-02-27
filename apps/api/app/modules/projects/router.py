"""Projects API router: CRUD, milestones, budget items, publish, stats."""

import uuid
from math import ceil

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.models.enums import ProjectStage, ProjectStatus, ProjectType
from app.modules.projects import service
from app.modules.projects.schemas import (
    BudgetItemCreateRequest,
    BudgetItemResponse,
    BudgetItemUpdateRequest,
    BusinessPlanActionResponse,
    BusinessPlanResultResponse,
    MilestoneCreateRequest,
    MilestoneResponse,
    MilestoneUpdateRequest,
    ProjectCreateRequest,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectStatsResponse,
    ProjectUpdateRequest,
    SignalScoreResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/projects", tags=["projects"])


# ── Helpers ─────────────────────────────────────────────────────────────────


async def _project_to_response(db, project) -> ProjectResponse:
    score = await service.get_latest_signal_score(db, project.id)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        project_type=project.project_type,
        status=project.status,
        stage=project.stage,
        geography_country=project.geography_country,
        geography_region=project.geography_region,
        geography_coordinates=project.geography_coordinates,
        technology_details=project.technology_details,
        capacity_mw=project.capacity_mw,
        total_investment_required=project.total_investment_required,
        currency=project.currency,
        target_close_date=project.target_close_date,
        cover_image_url=project.cover_image_url,
        is_published=project.is_published,
        published_at=project.published_at,
        latest_signal_score=score.overall_score if score else None,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


# ── Stats ───────────────────────────────────────────────────────────────────


@router.get(
    "/stats",
    response_model=ProjectStatsResponse,
    dependencies=[Depends(require_permission("view", "project"))],
)
async def get_project_stats(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated dashboard statistics for all projects in the org."""
    stats = await service.get_project_stats(db, current_user.org_id)
    return ProjectStatsResponse(**stats)


# ── Project CRUD ────────────────────────────────────────────────────────────


@router.get(
    "",
    response_model=ProjectListResponse,
    dependencies=[Depends(require_permission("view", "project"))],
)
async def list_projects(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    project_status: ProjectStatus | None = Query(None, alias="status"),
    project_type: ProjectType | None = Query(None, alias="type"),
    stage: ProjectStage | None = Query(None),
    geography: str | None = Query(None, max_length=100),
    score_min: int | None = Query(None, ge=0, le=100),
    score_max: int | None = Query(None, ge=0, le=100),
    search: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
):
    """List projects with filtering, pagination, and sorting."""
    items, total = await service.list_projects(
        db,
        current_user.org_id,
        status=project_status,
        project_type=project_type,
        stage=stage,
        geography=geography,
        score_min=score_min,
        score_max=score_max,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    responses = [await _project_to_response(db, p) for p in items]
    return ProjectListResponse(
        items=responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total > 0 else 0,
    )


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("create", "project"))],
)
async def create_project(
    body: ProjectCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""
    project = await service.create_project(
        db,
        current_user,
        name=body.name,
        project_type=body.project_type,
        description=body.description,
        geography_country=body.geography_country,
        geography_region=body.geography_region,
        geography_coordinates=body.geography_coordinates,
        technology_details=body.technology_details,
        capacity_mw=body.capacity_mw,
        total_investment_required=body.total_investment_required,
        currency=body.currency,
        target_close_date=body.target_close_date,
        stage=body.stage,
        status=body.status,
    )
    return await _project_to_response(db, project)


@router.get(
    "/{project_id}",
    response_model=ProjectDetailResponse,
    dependencies=[Depends(require_permission("view", "project"))],
)
async def get_project(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get project details with related counts."""
    try:
        project = await service.get_project(db, project_id, current_user.org_id)
        base = await _project_to_response(db, project)

        milestones = await service.list_milestones(db, project_id, current_user.org_id)
        budget_items = await service.list_budget_items(db, project_id, current_user.org_id)

        # Get document count
        from sqlalchemy import func, select
        from app.models.dataroom import Document
        doc_count_result = await db.execute(
            select(func.count())
            .select_from(Document)
            .where(
                Document.project_id == project_id,
                Document.is_deleted.is_(False),
            )
        )
        doc_count = doc_count_result.scalar_one()

        # Get latest signal score detail
        score = await service.get_latest_signal_score(db, project_id)
        signal_resp = None
        if score:
            signal_resp = SignalScoreResponse(
                overall_score=score.overall_score,
                technical_score=score.technical_score,
                financial_score=score.financial_score,
                esg_score=score.esg_score,
                regulatory_score=score.regulatory_score,
                team_score=score.team_score,
                gaps=score.gaps,
                strengths=score.strengths,
                model_used=score.model_used,
                version=score.version,
                calculated_at=score.calculated_at,
            )

        return ProjectDetailResponse(
            **base.model_dump(),
            milestone_count=len(milestones),
            budget_item_count=len(budget_items),
            document_count=doc_count,
            latest_signal=signal_resp,
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    dependencies=[Depends(require_permission("edit", "project"))],
)
async def update_project(
    project_id: uuid.UUID,
    body: ProjectUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a project."""
    try:
        project = await service.update_project(
            db,
            project_id,
            current_user.org_id,
            **body.model_dump(exclude_unset=True),
        )
        return await _project_to_response(db, project)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("delete", "project"))],
)
async def delete_project(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a project."""
    try:
        await service.delete_project(db, project_id, current_user.org_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{project_id}/publish",
    response_model=ProjectResponse,
    dependencies=[Depends(require_permission("edit", "project"))],
)
async def publish_project(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Publish a project to the marketplace."""
    try:
        project = await service.publish_project(db, project_id, current_user.org_id)
        return await _project_to_response(db, project)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ── Milestones ──────────────────────────────────────────────────────────────


@router.get(
    "/{project_id}/milestones",
    response_model=list[MilestoneResponse],
    dependencies=[Depends(require_permission("view", "project"))],
)
async def list_milestones(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List milestones for a project."""
    try:
        milestones = await service.list_milestones(db, project_id, current_user.org_id)
        return [
            MilestoneResponse(
                id=m.id,
                project_id=m.project_id,
                name=m.name,
                description=m.description,
                target_date=m.target_date,
                completed_date=m.completed_date,
                status=m.status,
                completion_pct=m.completion_pct,
                order_index=m.order_index,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in milestones
        ]
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{project_id}/milestones",
    response_model=MilestoneResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("edit", "project"))],
)
async def create_milestone(
    project_id: uuid.UUID,
    body: MilestoneCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a milestone to a project."""
    try:
        m = await service.create_milestone(
            db,
            project_id,
            current_user.org_id,
            name=body.name,
            description=body.description,
            target_date=body.target_date,
            order_index=body.order_index,
        )
        return MilestoneResponse(
            id=m.id, project_id=m.project_id, name=m.name, description=m.description,
            target_date=m.target_date, completed_date=m.completed_date, status=m.status,
            completion_pct=m.completion_pct, order_index=m.order_index,
            created_at=m.created_at, updated_at=m.updated_at,
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{project_id}/milestones/{milestone_id}",
    response_model=MilestoneResponse,
    dependencies=[Depends(require_permission("edit", "project"))],
)
async def update_milestone(
    project_id: uuid.UUID,
    milestone_id: uuid.UUID,
    body: MilestoneUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a milestone."""
    try:
        m = await service.update_milestone(
            db, milestone_id, project_id, current_user.org_id,
            **body.model_dump(exclude_unset=True),
        )
        return MilestoneResponse(
            id=m.id, project_id=m.project_id, name=m.name, description=m.description,
            target_date=m.target_date, completed_date=m.completed_date, status=m.status,
            completion_pct=m.completion_pct, order_index=m.order_index,
            created_at=m.created_at, updated_at=m.updated_at,
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{project_id}/milestones/{milestone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("edit", "project"))],
)
async def delete_milestone(
    project_id: uuid.UUID,
    milestone_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a milestone."""
    try:
        await service.delete_milestone(db, milestone_id, project_id, current_user.org_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Budget Items ────────────────────────────────────────────────────────────


@router.get(
    "/{project_id}/budget",
    response_model=list[BudgetItemResponse],
    dependencies=[Depends(require_permission("view", "project"))],
)
async def list_budget_items(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List budget items for a project."""
    try:
        items = await service.list_budget_items(db, project_id, current_user.org_id)
        return [
            BudgetItemResponse(
                id=b.id, project_id=b.project_id, category=b.category,
                description=b.description, estimated_amount=b.estimated_amount,
                actual_amount=b.actual_amount, currency=b.currency, status=b.status,
                created_at=b.created_at, updated_at=b.updated_at,
            )
            for b in items
        ]
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/{project_id}/budget",
    response_model=BudgetItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("edit", "project"))],
)
async def create_budget_item(
    project_id: uuid.UUID,
    body: BudgetItemCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a budget item to a project."""
    try:
        b = await service.create_budget_item(
            db, project_id, current_user.org_id,
            category=body.category, description=body.description,
            estimated_amount=body.estimated_amount, currency=body.currency,
        )
        return BudgetItemResponse(
            id=b.id, project_id=b.project_id, category=b.category,
            description=b.description, estimated_amount=b.estimated_amount,
            actual_amount=b.actual_amount, currency=b.currency, status=b.status,
            created_at=b.created_at, updated_at=b.updated_at,
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put(
    "/{project_id}/budget/{budget_id}",
    response_model=BudgetItemResponse,
    dependencies=[Depends(require_permission("edit", "project"))],
)
async def update_budget_item(
    project_id: uuid.UUID,
    budget_id: uuid.UUID,
    body: BudgetItemUpdateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a budget item."""
    try:
        b = await service.update_budget_item(
            db, budget_id, project_id, current_user.org_id,
            **body.model_dump(exclude_unset=True),
        )
        return BudgetItemResponse(
            id=b.id, project_id=b.project_id, category=b.category,
            description=b.description, estimated_amount=b.estimated_amount,
            actual_amount=b.actual_amount, currency=b.currency, status=b.status,
            created_at=b.created_at, updated_at=b.updated_at,
        )
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{project_id}/budget/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("edit", "project"))],
)
async def delete_budget_item(
    project_id: uuid.UUID,
    budget_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a budget item."""
    try:
        await service.delete_budget_item(db, budget_id, project_id, current_user.org_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── Business Plan AI ─────────────────────────────────────────────────────────

VALID_ACTION_TYPES = {
    "executive_summary", "financial_overview", "market_analysis",
    "risk_narrative", "esg_statement", "technical_summary", "investor_pitch",
}


@router.post(
    "/{project_id}/ai/generate/{action_type}",
    response_model=BusinessPlanActionResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def generate_business_plan_content(
    project_id: uuid.UUID,
    action_type: str,
    current_user: CurrentUser = Depends(require_permission("run_analysis", "analysis")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger async AI generation of business plan content."""
    if action_type not in VALID_ACTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"action_type must be one of {sorted(VALID_ACTION_TYPES)}",
        )
    try:
        task_log = await service.create_business_plan_task(
            db, project_id, current_user.org_id, current_user.user_id, action_type
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return BusinessPlanActionResponse(
        task_log_id=task_log.id,
        status=task_log.status.value,
        message=f"Generating {action_type.replace('_', ' ')}…",
    )


@router.get(
    "/{project_id}/ai/tasks/{task_log_id}",
    response_model=BusinessPlanResultResponse,
)
async def get_business_plan_result(
    project_id: uuid.UUID,
    task_log_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get the status and result of a business plan generation task."""
    result = await service.get_business_plan_result(
        db, task_log_id, project_id, current_user.org_id
    )
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result
