"""Insurance module API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.insurance import service
from app.modules.insurance.schemas import (
    InsuranceImpactResponse,
    InsuranceSummaryResponse,
    PolicyCreate,
    PolicyResponse,
    QuoteCreate,
    QuoteResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/insurance", tags=["insurance"])


@router.get(
    "/projects/{project_id}/impact",
    response_model=InsuranceImpactResponse,
)
async def get_insurance_impact(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Full AI-powered insurance impact analysis for a project.

    Returns recommended coverage types, estimated premium costs, risk reduction
    score, and financial impact on investor returns.
    """
    try:
        return await service.get_insurance_impact(db, current_user.org_id, project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/projects/{project_id}/summary",
    response_model=InsuranceSummaryResponse,
)
async def get_insurance_summary(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Lightweight insurance summary (no AI call — fast, for dashboard cards)."""
    try:
        return await service.get_insurance_summary(db, current_user.org_id, project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Quote CRUD ─────────────────────────────────────────────────────────────────


@router.post("/quotes", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    body: QuoteCreate,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Create an insurance quote for a project."""
    quote = await service.create_quote(db, current_user.org_id, body)
    return QuoteResponse.model_validate(quote)


@router.get("/quotes", response_model=list[QuoteResponse])
async def list_quotes(
    project_id: uuid.UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """List insurance quotes for the organisation, optionally filtered by project."""
    quotes = await service.list_quotes(db, current_user.org_id, project_id)
    return [QuoteResponse.model_validate(q) for q in quotes]


@router.delete("/quotes/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete an insurance quote."""
    try:
        await service.delete_quote(db, current_user.org_id, quote_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Policy CRUD ────────────────────────────────────────────────────────────────


@router.post("/policies", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    body: PolicyCreate,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Convert a quote into an active insurance policy."""
    try:
        policy = await service.create_policy(db, current_user.org_id, body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return PolicyResponse.model_validate(policy)


@router.get("/policies", response_model=list[PolicyResponse])
async def list_policies(
    project_id: uuid.UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """List insurance policies for the organisation, optionally filtered by project."""
    policies = await service.list_policies(db, current_user.org_id, project_id)
    return [PolicyResponse.model_validate(p) for p in policies]


@router.delete("/policies/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("create", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Cancel/soft-delete an insurance policy."""
    try:
        await service.delete_policy(db, current_user.org_id, policy_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
