"""Alley Risk API — project holder view of project risks with mitigation tracking."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.alley.risk import service
from app.modules.alley.risk.schemas import (
    DomainRiskResponse,
    EvidenceLinkRequest,
    MitigationProgressResponse,
    MitigationUpdateRequest,
    ProjectRiskDetailResponse,
    RiskListResponse,
    RunCheckResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/alley/risk", tags=["alley-risk"])


@router.get("", response_model=RiskListResponse, summary="Risk summaries for all my projects")
async def list_risks(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_risk_summaries(db, current_user.org_id)


@router.get(
    "/domains",
    response_model=DomainRiskResponse,
    summary="5-domain risk breakdown across portfolio",
)
async def get_domain_breakdown(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_domain_breakdown(db, current_user.org_id)


@router.get(
    "/{project_id}",
    response_model=ProjectRiskDetailResponse,
    summary="Full risk detail for my project",
)
async def get_risk_detail(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_project_risk_detail(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{project_id}/check",
    response_model=RunCheckResponse,
    summary="Run new risk check for a project",
)
async def run_risk_check(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.run_risk_check(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{project_id}/items/{risk_id}", summary="Update mitigation status for a risk item")
async def update_mitigation(
    project_id: uuid.UUID,
    risk_id: uuid.UUID,
    body: MitigationUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        rec = await service.update_mitigation_status(
            db, project_id, risk_id, current_user.org_id, body.status, body.notes
        )
        return {"id": str(rec.id), "status": rec.status}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{project_id}/items/{risk_id}/evidence",
    summary="Link document as evidence for risk mitigation",
)
async def add_evidence(
    project_id: uuid.UUID,
    risk_id: uuid.UUID,
    body: EvidenceLinkRequest,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        rec = await service.add_evidence(
            db, project_id, risk_id, current_user.org_id, body.document_id
        )
        return {"id": str(rec.id), "evidence_count": len(rec.evidence_document_ids or [])}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/{project_id}/progress",
    response_model=MitigationProgressResponse,
    summary="Risk mitigation progress",
)
async def get_progress(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await service.get_mitigation_progress(db, project_id, current_user.org_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
