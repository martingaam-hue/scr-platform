"""Deal Flow Analytics API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.deal_flow import service
from app.modules.deal_flow.schemas import (
    FunnelResponse,
    PipelineValueResponse,
    TransitionCreate,
    TransitionResponse,
    VelocityResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()
router = APIRouter(prefix="/deal-flow", tags=["deal-flow"])


@router.get("/funnel", response_model=FunnelResponse)
async def get_funnel(
    period_days: int = Query(90, ge=1, le=730, description="Look-back window in days"),
    investor_id: uuid.UUID | None = Query(None, description="Filter by investor"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FunnelResponse:
    """Return deal funnel metrics for the organisation."""
    logger.info(
        "deal_flow_funnel",
        org_id=str(current_user.org_id),
        period_days=period_days,
    )
    return await service.get_funnel(
        db,
        org_id=current_user.org_id,
        period_days=period_days,
        investor_id=investor_id,
    )


@router.post("/transition", response_model=TransitionResponse, status_code=201)
async def record_transition(
    body: TransitionCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TransitionResponse:
    """Record a deal stage transition event."""
    transition = await service.record_transition(
        db,
        org_id=current_user.org_id,
        project_id=body.project_id,
        to_stage=body.to_stage,
        from_stage=body.from_stage,
        reason=body.reason,
        investor_id=body.investor_id,
        user_id=current_user.user_id,
        metadata=body.metadata,
    )
    logger.info(
        "deal_stage_transition_recorded",
        org_id=str(current_user.org_id),
        project_id=str(body.project_id),
        to_stage=body.to_stage,
    )
    return TransitionResponse.model_validate(transition)


@router.get("/pipeline-value", response_model=PipelineValueResponse)
async def get_pipeline_value(
    investor_id: uuid.UUID | None = Query(None, description="Filter by investor"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PipelineValueResponse:
    """Return total pipeline value aggregated by current deal stage."""
    return await service.get_pipeline_value(
        db,
        org_id=current_user.org_id,
        investor_id=investor_id,
    )


@router.get("/velocity", response_model=VelocityResponse)
async def get_velocity(
    investor_id: uuid.UUID | None = Query(None, description="Filter by investor"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> VelocityResponse:
    """Return deal velocity — average time per stage and trend."""
    return await service.get_velocity(
        db,
        org_id=current_user.org_id,
        investor_id=investor_id,
    )


# ── Bulk Operations ─────────────────────────────────────────────────────────


class BulkStageRequest(BaseModel):
    deal_ids: list[uuid.UUID]
    stage: str


@router.post(
    "/bulk/stage",
    dependencies=[Depends(require_permission("write", "projects"))],
)
async def bulk_update_stage(
    req: BulkStageRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Move multiple deals to the same stage in one request.

    Calls ``record_transition`` for each deal ID. Failed transitions
    (e.g. project not found) are collected and returned in ``failed``.
    Maximum 100 deals per request.
    """
    if len(req.deal_ids) > 100:
        raise HTTPException(status_code=400, detail="Max 100 items per bulk request")

    updated = 0
    failed: list[str] = []

    for deal_id in req.deal_ids:
        try:
            await service.record_transition(
                db,
                org_id=current_user.org_id,
                project_id=deal_id,
                to_stage=req.stage,
                user_id=current_user.user_id,
            )
            updated += 1
        except Exception as exc:
            logger.warning("bulk_stage.deal_failed", deal_id=str(deal_id), error=str(exc))
            failed.append(str(deal_id))

    return {"updated": updated, "failed": failed}
