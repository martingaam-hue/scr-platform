"""Meeting Prep API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.meeting_prep import service
from app.modules.meeting_prep.schemas import (
    BriefingListResponse,
    BriefingResponse,
    GenerateBriefingRequest,
    UpdateBriefingRequest,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/meeting-prep", tags=["meeting-prep"])


@router.post("/briefings", response_model=BriefingResponse, status_code=status.HTTP_201_CREATED)
async def generate_briefing(
    body: GenerateBriefingRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI meeting briefing for a project."""
    briefing = await service.generate_briefing(
        db,
        org_id=current_user.org_id,
        project_id=body.project_id,
        user_id=current_user.user_id,
        meeting_type=body.meeting_type,
        meeting_date=body.meeting_date,
        previous_meeting_date=body.previous_meeting_date,
    )
    await db.commit()
    await db.refresh(briefing)
    logger.info(
        "meeting_prep.generated",
        briefing_id=str(briefing.id),
        project_id=str(body.project_id),
        meeting_type=body.meeting_type,
    )
    return BriefingResponse.model_validate(briefing)


@router.get("/briefings", response_model=BriefingListResponse)
async def list_briefings(
    project_id: uuid.UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """List meeting briefings for the current org, optionally filtered by project."""
    briefings = await service.list_briefings(db, org_id=current_user.org_id, project_id=project_id)
    return BriefingListResponse(
        items=[BriefingResponse.model_validate(b) for b in briefings],
        total=len(briefings),
    )


@router.get("/briefings/{briefing_id}", response_model=BriefingResponse)
async def get_briefing(
    briefing_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    briefing = await service.get_briefing(db, briefing_id=briefing_id, org_id=current_user.org_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")
    return BriefingResponse.model_validate(briefing)


@router.put("/briefings/{briefing_id}", response_model=BriefingResponse)
async def update_briefing(
    briefing_id: uuid.UUID,
    body: UpdateBriefingRequest,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    """Save user edits as custom overrides (merged with AI content on read)."""
    briefing = await service.update_briefing(
        db, briefing_id=briefing_id, org_id=current_user.org_id, custom_overrides=body.custom_overrides
    )
    if not briefing:
        raise HTTPException(status_code=404, detail="Briefing not found")
    await db.commit()
    await db.refresh(briefing)
    return BriefingResponse.model_validate(briefing)


@router.delete("/briefings/{briefing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_briefing(
    briefing_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    deleted = await service.delete_briefing(db, briefing_id=briefing_id, org_id=current_user.org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Briefing not found")
    await db.commit()
