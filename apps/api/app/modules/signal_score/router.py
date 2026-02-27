"""Signal Score API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.signal_score import service
from app.modules.signal_score.criteria import DIMENSIONS
from app.modules.signal_score.schemas import (
    CalculateAcceptedResponse,
    DimensionScoreResponse,
    CriterionScoreResponse,
    GapItem,
    GapsResponse,
    ScoreHistoryItem,
    ScoreHistoryResponse,
    SignalScoreDetailResponse,
    TaskStatusResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/signal-score", tags=["signal-score"])


# ── Task status (fixed path before parameterised) ──────────────────────────


@router.get("/task/{task_log_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_log_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check status of a signal score calculation task."""
    task_log = await service.get_task_status(db, task_log_id, current_user.org_id)
    if not task_log:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskStatusResponse(
        id=task_log.id,
        status=task_log.status.value,
        error_message=task_log.error_message,
    )


# ── Calculate ───────────────────────────────────────────────────────────────


@router.post(
    "/calculate/{project_id}",
    response_model=CalculateAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def calculate_score(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("run_analysis", "analysis")),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a new signal score calculation."""
    try:
        task_log = await service.trigger_calculation(
            db, project_id, current_user.org_id, current_user.user_id
        )
        await db.commit()
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    return CalculateAcceptedResponse(
        task_log_id=task_log.id,
        status="pending",
        message="Signal score calculation started",
    )


@router.post(
    "/{project_id}/recalculate",
    response_model=CalculateAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def recalculate_score(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("run_analysis", "analysis")),
    db: AsyncSession = Depends(get_db),
):
    """Force recalculation of signal score (creates new version)."""
    try:
        task_log = await service.trigger_calculation(
            db, project_id, current_user.org_id, current_user.user_id
        )
        await db.commit()
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    return CalculateAcceptedResponse(
        task_log_id=task_log.id,
        status="pending",
        message="Signal score recalculation started",
    )


# ── Read endpoints ──────────────────────────────────────────────────────────


@router.get("/{project_id}", response_model=SignalScoreDetailResponse)
async def get_latest_score(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get latest signal score with full dimension breakdown."""
    try:
        score = await service.get_latest_score(
            db, project_id, current_user.org_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    if not score:
        raise HTTPException(status_code=404, detail="No signal score found")

    return _build_detail_response(score)


@router.get("/{project_id}/details", response_model=SignalScoreDetailResponse)
async def get_score_details(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed scoring breakdown with criteria and AI assessments."""
    try:
        score = await service.get_latest_score(
            db, project_id, current_user.org_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    if not score:
        raise HTTPException(status_code=404, detail="No signal score found")

    return _build_detail_response(score)


@router.get("/{project_id}/gaps", response_model=GapsResponse)
async def get_gaps(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get gap analysis with prioritized recommendations."""
    try:
        score = await service.get_latest_score(
            db, project_id, current_user.org_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    if not score:
        raise HTTPException(status_code=404, detail="No signal score found")

    gaps_data = score.gaps or {}
    items = [GapItem(**item) for item in gaps_data.get("items", [])]
    return GapsResponse(items=items, total=len(items))


@router.get("/{project_id}/history", response_model=ScoreHistoryResponse)
async def get_score_history(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get signal score history across all versions."""
    try:
        scores = await service.get_score_history(
            db, project_id, current_user.org_id
        )
    except LookupError:
        raise HTTPException(status_code=404, detail="Project not found")

    items = [
        ScoreHistoryItem(
            version=s.version,
            overall_score=s.overall_score,
            technical_score=s.technical_score,
            financial_score=s.financial_score,
            esg_score=s.esg_score,
            regulatory_score=s.regulatory_score,
            team_score=s.team_score,
            calculated_at=s.calculated_at,
        )
        for s in scores
    ]
    return ScoreHistoryResponse(items=items)


# ── Helpers ─────────────────────────────────────────────────────────────────


def _build_detail_response(score) -> SignalScoreDetailResponse:
    """Build detailed response from SignalScore model."""
    scoring_details = score.scoring_details or {}
    dimensions_data = scoring_details.get("dimensions", {})

    dimensions = []
    for dim in DIMENSIONS:
        dim_data = dimensions_data.get(dim.id, {})
        criteria = [
            CriterionScoreResponse(
                id=c.get("id", ""),
                name=c.get("name", ""),
                max_points=c.get("max_points", 0),
                score=c.get("score", 0),
                has_document=c.get("has_document", False),
                ai_assessment=c.get("ai_assessment"),
            )
            for c in dim_data.get("criteria", [])
        ]
        dimensions.append(
            DimensionScoreResponse(
                id=dim.id,
                name=dim.name,
                weight=dim.weight,
                score=dim_data.get("score", 0),
                completeness_score=dim_data.get("completeness_score", 0),
                quality_score=dim_data.get("quality_score", 0),
                criteria=criteria,
            )
        )

    return SignalScoreDetailResponse(
        id=score.id,
        project_id=score.project_id,
        overall_score=score.overall_score,
        dimensions=dimensions,
        model_used=score.model_used or "deterministic",
        version=score.version,
        calculated_at=score.calculated_at,
    )
