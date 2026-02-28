"""Investor Readiness Certification API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.certification import service
from app.modules.certification.schemas import (
    CertificationBadge,
    CertificationRequirementsResponse,
    CertificationResponse,
    LeaderboardEntry,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/certification", tags=["certification"])


@router.get("/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return certified projects leaderboard for the organisation, ordered by score."""
    entries = await service.get_certified_projects(db, current_user.org_id)
    return entries


@router.get("/{project_id}", response_model=CertificationResponse)
async def get_certification(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full certification status for a project."""
    from sqlalchemy import select
    from app.models.certification import InvestorReadinessCertification

    stmt = select(InvestorReadinessCertification).where(
        InvestorReadinessCertification.project_id == project_id,
        InvestorReadinessCertification.org_id == current_user.org_id,
        InvestorReadinessCertification.is_deleted.is_(False),
    )
    result = await db.execute(stmt)
    cert = result.scalar_one_or_none()

    if cert is None:
        raise HTTPException(status_code=404, detail="No certification record found for this project")

    return CertificationResponse.model_validate(cert)


@router.get("/{project_id}/badge", response_model=CertificationBadge)
async def get_badge(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get badge data for a project. Returns certified=False if not certified."""
    return await service.get_certification_badge(db, project_id)


@router.get("/{project_id}/requirements", response_model=CertificationRequirementsResponse)
async def get_requirements(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check what a project needs to achieve Investor Readiness Certification."""
    return await service.get_certification_requirements(
        db, project_id, current_user.org_id
    )


@router.post("/{project_id}/evaluate", response_model=CertificationResponse)
async def evaluate_certification(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a re-evaluation of certification status for a project."""
    try:
        cert = await service.evaluate_certification(
            db, project_id, current_user.org_id
        )
    except Exception as exc:
        logger.error(
            "certification_evaluation_error",
            project_id=str(project_id),
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail="Certification evaluation failed")

    return CertificationResponse.model_validate(cert)
