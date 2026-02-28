"""Portfolio stress test API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.stress_test import service
from app.modules.stress_test.engine import PREDEFINED_SCENARIOS
from app.modules.stress_test.schemas import (
    RunStressTestRequest,
    ScenarioResponse,
    StressTestListResponse,
    StressTestResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/stress-test", tags=["stress-test"])


@router.get("/scenarios", response_model=list[ScenarioResponse])
async def list_scenarios(
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
):
    return [
        ScenarioResponse(key=k, name=v["name"], description=v["description"], params=v["params"])
        for k, v in PREDEFINED_SCENARIOS.items()
    ]


@router.post("/run", response_model=StressTestResponse, status_code=status.HTTP_201_CREATED)
async def run_stress_test(
    body: RunStressTestRequest,
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    try:
        run = await service.run_stress_test(
            db,
            org_id=current_user.org_id,
            user_id=current_user.user_id,
            portfolio_id=body.portfolio_id,
            scenario_key=body.scenario_key,
            custom_params=body.custom_params,
            custom_name=body.custom_name,
            simulations=body.simulations,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return StressTestResponse.model_validate(run)


@router.get("/portfolio/{portfolio_id}", response_model=StressTestListResponse)
async def list_stress_tests(
    portfolio_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    runs = await service.list_stress_tests(db, current_user.org_id, portfolio_id)
    items = [StressTestResponse.model_validate(r) for r in runs]
    return StressTestListResponse(items=items, total=len(items))


@router.get("/{run_id}", response_model=StressTestResponse)
async def get_stress_test(
    run_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "portfolio")),
    db: AsyncSession = Depends(get_db),
):
    run = await service.get_stress_test(db, run_id, current_user.org_id)
    if not run:
        raise HTTPException(status_code=404, detail="Stress test run not found")
    return StressTestResponse.model_validate(run)
