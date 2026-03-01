"""Cashflow Pacing — FastAPI router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.pacing.schemas import (
    AssumptionSummary,
    CreateAssumptionRequest,
    PacingResponse,
    ProjectionRow,
    UpdateActualsRequest,
)
from app.modules.pacing.service import PacingService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()
router = APIRouter(prefix="/pacing", tags=["Cashflow Pacing"])


@router.post(
    "/portfolios/{portfolio_id}/assumptions",
    response_model=PacingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assumption(
    portfolio_id: uuid.UUID,
    body: CreateAssumptionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PacingResponse:
    """Create pacing assumptions and auto-generate J-curve projections for a portfolio."""
    # Ensure the portfolio_id in path matches body
    body_with_portfolio = body.model_copy(update={"portfolio_id": portfolio_id})
    svc = PacingService(db, current_user.org_id)
    try:
        result = await svc.create_assumption(body_with_portfolio)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error(
            "pacing_create_assumption_error",
            portfolio_id=str(portfolio_id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create pacing assumption",
        ) from exc
    return result


@router.get("/portfolios/{portfolio_id}", response_model=PacingResponse)
async def get_pacing(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PacingResponse:
    """Return the active pacing model (all scenarios) for a portfolio."""
    svc = PacingService(db, current_user.org_id)
    try:
        result = await svc.get_pacing(portfolio_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return result


@router.get(
    "/portfolios/{portfolio_id}/assumptions",
    response_model=list[AssumptionSummary],
)
async def list_assumptions(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AssumptionSummary]:
    """List all pacing assumptions for a portfolio."""
    svc = PacingService(db, current_user.org_id)
    return await svc.list_assumptions(portfolio_id)


@router.put(
    "/assumptions/{assumption_id}/actuals",
    response_model=ProjectionRow,
)
async def update_actuals(
    assumption_id: uuid.UUID,
    body: UpdateActualsRequest,
    scenario: str = "base",
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectionRow:
    """Update actual cashflow data for a specific year and scenario."""
    svc = PacingService(db, current_user.org_id)
    try:
        row = await svc.update_actuals(assumption_id, body, scenario)
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        logger.error(
            "pacing_update_actuals_error",
            assumption_id=str(assumption_id),
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update actuals",
        ) from exc
    return row
