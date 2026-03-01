"""Business Plans CRUD API router."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.business_plans.schemas import (
    BusinessPlanCreate,
    BusinessPlanResponse,
    BusinessPlanUpdate,
)
from app.modules.business_plans.service import BusinessPlanService
from app.schemas.auth import CurrentUser

router = APIRouter(prefix="/business-plans", tags=["Business Plans"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BusinessPlanResponse,
)
async def create_plan(
    body: BusinessPlanCreate,
    current_user: CurrentUser = Depends(require_permission("create", "business_plan")),
    db: AsyncSession = Depends(get_db),
) -> BusinessPlanResponse:
    """Create a new business plan for a project."""
    svc = BusinessPlanService(db, current_user.org_id)
    plan = await svc.create(current_user.user_id, body)
    return BusinessPlanResponse.model_validate(plan)


@router.get("", response_model=list[BusinessPlanResponse])
async def list_plans(
    project_id: Optional[uuid.UUID] = None,
    current_user: CurrentUser = Depends(require_permission("view", "business_plan")),
    db: AsyncSession = Depends(get_db),
) -> list[BusinessPlanResponse]:
    """List business plans for the organisation, optionally filtered by project."""
    svc = BusinessPlanService(db, current_user.org_id)
    plans = await svc.list(project_id)
    return [BusinessPlanResponse.model_validate(p) for p in plans]


@router.get("/{plan_id}", response_model=BusinessPlanResponse)
async def get_plan(
    plan_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "business_plan")),
    db: AsyncSession = Depends(get_db),
) -> BusinessPlanResponse:
    """Retrieve a single business plan by ID."""
    svc = BusinessPlanService(db, current_user.org_id)
    plan = await svc.get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Business plan not found")
    return BusinessPlanResponse.model_validate(plan)


@router.patch("/{plan_id}", response_model=BusinessPlanResponse)
async def update_plan(
    plan_id: uuid.UUID,
    body: BusinessPlanUpdate,
    current_user: CurrentUser = Depends(require_permission("edit", "business_plan")),
    db: AsyncSession = Depends(get_db),
) -> BusinessPlanResponse:
    """Partially update a business plan."""
    svc = BusinessPlanService(db, current_user.org_id)
    plan = await svc.update(plan_id, body)
    if not plan:
        raise HTTPException(status_code=404, detail="Business plan not found")
    return BusinessPlanResponse.model_validate(plan)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("delete", "business_plan")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a business plan."""
    svc = BusinessPlanService(db, current_user.org_id)
    deleted = await svc.delete(plan_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Business plan not found")
