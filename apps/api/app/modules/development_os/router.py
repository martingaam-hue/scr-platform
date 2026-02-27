"""Development OS API router — construction lifecycle management."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.development_os import service
from app.modules.development_os.schemas import (
    DevelopmentOSResponse,
    MilestoneCreate,
    MilestoneResponse,
    MilestoneUpdate,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/development-os", tags=["development-os"])


@router.get("/{project_id}", response_model=DevelopmentOSResponse)
async def get_development_overview(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> DevelopmentOSResponse:
    """Get full Development OS overview — phases, milestones, procurement."""
    try:
        return await service.get_development_overview(db, current_user.org_id, project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/{project_id}/milestones", response_model=list[MilestoneResponse])
async def list_milestones(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> list[MilestoneResponse]:
    """List all milestones for a project."""
    try:
        return await service.list_milestones(db, current_user.org_id, project_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post(
    "/{project_id}/milestones",
    response_model=MilestoneResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_milestone(
    project_id: uuid.UUID,
    body: MilestoneCreate,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
) -> MilestoneResponse:
    """Create a new milestone for a project."""
    try:
        result = await service.create_milestone(db, current_user.org_id, project_id, body)
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("development_os.create_milestone.error", error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to create milestone")


@router.put("/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    milestone_id: uuid.UUID,
    body: MilestoneUpdate,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
) -> MilestoneResponse:
    """Update an existing milestone."""
    try:
        result = await service.update_milestone(db, current_user.org_id, milestone_id, body)
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("development_os.update_milestone.error", milestone_id=str(milestone_id), error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to update milestone")


@router.delete("/milestones/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_milestone(
    milestone_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a milestone."""
    try:
        await service.delete_milestone(db, current_user.org_id, milestone_id)
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("development_os.delete_milestone.error", milestone_id=str(milestone_id), error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to delete milestone")
