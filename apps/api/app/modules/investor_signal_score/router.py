"""Investor Signal Score API router."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.investor_signal_score import service
from app.modules.investor_signal_score.schemas import (
    DealAlignmentRequest,
    DealAlignmentResponse,
    InvestorSignalScoreResponse,
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
    """Trigger a fresh calculation of the Investor Signal Score from mandate data."""
    try:
        result = await service.calculate_score(db, current_user.org_id)
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/deal-alignment", response_model=DealAlignmentResponse)
async def get_deal_alignment(
    body: DealAlignmentRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DealAlignmentResponse:
    """Compute alignment between investor signal score and a specific project."""
    try:
        return await service.get_deal_alignment(db, current_user.org_id, body.project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
