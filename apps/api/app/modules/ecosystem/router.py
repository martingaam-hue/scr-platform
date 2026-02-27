"""Ecosystem API router — stakeholder relationship mapping."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.ecosystem import service
from app.modules.ecosystem.schemas import (
    EcosystemMapResponse,
    RelationshipCreate,
    StakeholderCreate,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/ecosystem", tags=["ecosystem"])


@router.get("", response_model=EcosystemMapResponse)
async def get_org_ecosystem(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> EcosystemMapResponse:
    """Get the organisation-level ecosystem stakeholder map."""
    result = await service.get_ecosystem_map(db, current_user.org_id, project_id=None)
    await db.commit()
    return result


@router.get("/{project_id}", response_model=EcosystemMapResponse)
async def get_project_ecosystem(
    project_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
) -> EcosystemMapResponse:
    """Get the project-specific ecosystem stakeholder map."""
    try:
        result = await service.get_ecosystem_map(db, current_user.org_id, project_id=project_id)
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{project_id}/stakeholders", response_model=EcosystemMapResponse)
async def add_stakeholder(
    project_id: uuid.UUID,
    body: StakeholderCreate,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
) -> EcosystemMapResponse:
    """Add a stakeholder node to a project's ecosystem map."""
    try:
        result = await service.add_stakeholder(db, current_user.org_id, project_id, body)
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("ecosystem.add_stakeholder.error", project_id=str(project_id), error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to add stakeholder")


@router.post("/{project_id}/relationships", response_model=EcosystemMapResponse)
async def add_relationship(
    project_id: uuid.UUID,
    body: RelationshipCreate,
    current_user: CurrentUser = Depends(require_permission("edit", "project")),
    db: AsyncSession = Depends(get_db),
) -> EcosystemMapResponse:
    """Add a relationship edge between two stakeholders."""
    try:
        result = await service.add_relationship(db, current_user.org_id, project_id, body)
        await db.commit()
        return result
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("ecosystem.add_relationship.error", project_id=str(project_id), error=str(exc))
        raise HTTPException(status_code=500, detail="Failed to add relationship")
