"""Investor Signal Score API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.investor_signal_score import service
from app.modules.investor_signal_score.schemas import (
    BenchmarkResponse,
    DealAlignmentRequest,
    DealAlignmentResponse,
    DimensionDetailResponse,
    ImprovementAction,
    InvestorSignalScoreResponse,
    ScoreFactorItem,
    ScoreHistoryItem,
    TopMatchItem,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/investor-signal-score", tags=["investor-signal-score"])


@router.get("", response_model=InvestorSignalScoreResponse)
async def get_latest_score(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestorSignalScoreResponse:
    """Get the most recently calculated Investor Signal Score for the org."""
    score = await service.get_latest_score(db, current_user.org_id)
    if score is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No investor signal score found. Use POST /investor-signal-score/calculate to compute one.",
        )
    return score


@router.post(
    "/calculate",
    response_model=InvestorSignalScoreResponse,
    status_code=status.HTTP_201_CREATED,
)
async def calculate_score(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> InvestorSignalScoreResponse:
    """Trigger a fresh calculation of the Investor Signal Score from all platform data."""
    try:
        result = await service.calculate_score(db, current_user.org_id)
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/history", response_model=list[ScoreHistoryItem])
async def get_score_history(
    limit: int = Query(default=12, ge=1, le=50),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScoreHistoryItem]:
    """Return historical score records for trend/sparkline display."""
    return await service.get_score_history(db, current_user.org_id, limit=limit)


@router.get("/improvement-plan", response_model=list[ImprovementAction])
async def get_improvement_plan(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ImprovementAction]:
    """Return prioritised improvement actions from the latest score."""
    return await service.get_improvement_plan(db, current_user.org_id)


@router.get("/factors", response_model=list[ScoreFactorItem])
async def get_score_factors(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ScoreFactorItem]:
    """Return positive and negative score factors from the latest score."""
    return await service.get_score_factors(db, current_user.org_id)


@router.get("/benchmark", response_model=BenchmarkResponse)
async def get_benchmark(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BenchmarkResponse:
    """Compare this org's score against the platform distribution."""
    score = await service.get_latest_score(db, current_user.org_id)
    if score is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No score yet — calculate first.",
        )
    return await service.get_benchmark(db, current_user.org_id)


@router.get("/top-matches", response_model=list[TopMatchItem])
async def get_top_matches(
    limit: int = Query(default=5, ge=1, le=20),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[TopMatchItem]:
    """Return top deal-alignment matches for this investor."""
    return await service.get_top_matches(db, current_user.org_id, limit=limit)


@router.get("/details/{dimension}", response_model=DimensionDetailResponse)
async def get_dimension_details(
    dimension: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DimensionDetailResponse:
    """Return full criteria breakdown for a specific dimension."""
    result = await service.get_dimension_details(db, current_user.org_id, dimension)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dimension '{dimension}' not found or no score calculated yet.",
        )
    return result


@router.get("/deal-alignment/{project_id}", response_model=DealAlignmentResponse)
async def get_deal_alignment_by_project(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DealAlignmentResponse:
    """Compute alignment between investor signal score and a specific project."""
    try:
        return await service.get_deal_alignment(db, current_user.org_id, project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/deal-alignment", response_model=DealAlignmentResponse)
async def get_deal_alignment(
    body: DealAlignmentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DealAlignmentResponse:
    """Compute alignment between investor signal score and a specific project (POST body)."""
    try:
        return await service.get_deal_alignment(db, current_user.org_id, body.project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
