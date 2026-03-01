"""Lineage API router — data provenance and computation tracing."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.core.database import get_db
from app.modules.lineage.service import LineageService
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()
router = APIRouter(prefix="/lineage", tags=["lineage"])


def _lineage_to_dict(l) -> dict:
    return {
        "id": str(l.id),
        "entity_type": l.entity_type,
        "entity_id": str(l.entity_id),
        "field_name": l.field_name,
        "field_value": l.field_value,
        "source_type": l.source_type,
        "source_id": str(l.source_id) if l.source_id else None,
        "source_detail": l.source_detail,
        "source_version": l.source_version,
        "computation_chain": l.computation_chain,
        "recorded_at": l.recorded_at.isoformat(),
    }


@router.get("/{entity_type}/{entity_id}")
async def get_entity_lineage(
    entity_type: str,
    entity_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all lineage records for an entity."""
    svc = LineageService(db, current_user.org_id)
    records = await svc.get_lineage(entity_type, entity_id)
    return [_lineage_to_dict(r) for r in records]


@router.get("/{entity_type}/{entity_id}/{field_name}")
async def get_field_lineage(
    entity_type: str,
    entity_id: uuid.UUID,
    field_name: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get lineage records for a specific field on an entity."""
    svc = LineageService(db, current_user.org_id)
    records = await svc.get_lineage(entity_type, entity_id, field_name)
    return [_lineage_to_dict(r) for r in records]


@router.get("/trace/{entity_type}/{entity_id}/{field_name}")
async def get_full_trace(
    entity_type: str,
    entity_id: uuid.UUID,
    field_name: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get complete derivation chain with document details."""
    svc = LineageService(db, current_user.org_id)
    trace = await svc.get_full_trace(entity_type, entity_id, field_name)
    if not trace:
        raise HTTPException(status_code=404, detail=f"No lineage found for {entity_type}/{entity_id}/{field_name}")
    return trace
