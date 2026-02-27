"""Equity Calculator API router — all calculations are deterministic Python."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.equity_calculator import service
from app.modules.equity_calculator.schemas import (
    CompareRequest,
    CompareResponse,
    EquityScenarioRequest,
    EquityScenarioResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/equity-calculator", tags=["equity-calculator"])


@router.post(
    "/scenarios",
    response_model=EquityScenarioResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_scenario(
    body: EquityScenarioRequest,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
) -> EquityScenarioResponse:
    """Create and persist a new equity scenario with calculated metrics."""
    try:
        result = await service.create_scenario(db, current_user.org_id, body)
        await db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/scenarios", response_model=list[EquityScenarioResponse])
async def list_scenarios(
    project_id: uuid.UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> list[EquityScenarioResponse]:
    """List equity scenarios for the org, optionally filtered by project."""
    return await service.list_scenarios(db, current_user.org_id, project_id)


@router.get("/scenarios/{scenario_id}", response_model=EquityScenarioResponse)
async def get_scenario(
    scenario_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> EquityScenarioResponse:
    """Get a single equity scenario by ID."""
    try:
        return await service.get_scenario(db, scenario_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/compare", response_model=CompareResponse)
async def compare_scenarios(
    body: CompareRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> CompareResponse:
    """Side-by-side comparison of 2–5 equity scenarios."""
    return await service.compare_scenarios(
        db, body.scenario_ids, current_user.org_id
    )
