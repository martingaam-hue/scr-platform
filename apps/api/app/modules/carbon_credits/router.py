"""Carbon Credits API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.carbon_credits import service
from app.modules.carbon_credits.schemas import (
    CarbonCreditResponse,
    CarbonCreditUpdate,
    CarbonEstimateResult,
    MethodologyResponse,
    PricingTrendPoint,
    VerificationStatusUpdate,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/carbon", tags=["carbon_credits"])


@router.post("/estimate/{project_id}", response_model=dict)
async def estimate_carbon_credits(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Deterministic carbon credit estimation based on project type and capacity."""
    try:
        estimate, cc = await service.estimate_credits(
            db, project_id, current_user.org_id
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {"estimate": estimate.model_dump(), "credit_record": cc.model_dump()}


@router.get("/{project_id}", response_model=CarbonCreditResponse)
async def get_carbon_credit(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Get carbon credit details for a project."""
    try:
        return await service.get_carbon_credit(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/{project_id}", response_model=CarbonCreditResponse)
async def update_carbon_credit(
    project_id: uuid.UUID,
    body: CarbonCreditUpdate,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Update carbon credit record fields."""
    try:
        return await service.update_carbon_credit(
            db, project_id, current_user.org_id, body
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/{project_id}/verification-status", response_model=CarbonCreditResponse)
async def update_verification_status(
    project_id: uuid.UUID,
    body: VerificationStatusUpdate,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Update verification status of a carbon credit."""
    try:
        return await service.update_verification_status(
            db, project_id, current_user.org_id,
            body.verification_status, body.verification_body
        )
    except (LookupError, ValueError) as exc:
        status_code = 404 if isinstance(exc, LookupError) else 422
        raise HTTPException(status_code=status_code, detail=str(exc))


@router.post("/{project_id}/submit-verification", status_code=status.HTTP_202_ACCEPTED)
async def submit_verification(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Start verification process — sets status to 'submitted'."""
    try:
        cc = await service.update_verification_status(
            db, project_id, current_user.org_id, "submitted", None
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return {
        "status": "accepted",
        "message": "Verification submission initiated",
        "credit_id": str(cc.id),
    }


@router.post("/{project_id}/list-marketplace", response_model=CarbonCreditResponse)
async def list_on_marketplace(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
):
    """List carbon credits on the marketplace (transitions status to 'listed')."""
    try:
        return await service.list_on_marketplace(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/pricing-trends", response_model=list[PricingTrendPoint])
async def get_pricing_trends(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Historical carbon price trends across markets."""
    return service.get_pricing_trends()


@router.get("/methodologies", response_model=list[MethodologyResponse])
async def get_methodologies(
    current_user: CurrentUser = Depends(get_current_user),
):
    """Available carbon credit verification methodologies."""
    return service.get_methodologies()
