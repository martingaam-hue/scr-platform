"""Blockchain audit trail API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.blockchain_audit import service
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/blockchain-audit", tags=["blockchain-audit"])


class AnchorResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    entity_type: str
    entity_id: uuid.UUID
    data_hash: str
    merkle_root: str | None
    chain: str
    tx_hash: str | None
    block_number: int | None
    status: str
    anchored_at: str | None = None

    class Config:
        from_attributes = True


@router.get("/verify/{entity_type}/{entity_id}")
async def verify_anchor(
    entity_type: str,
    entity_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    return await service.verify_anchor(db, entity_type, entity_id)


@router.get("/anchors/{entity_type}/{entity_id}", response_model=list[AnchorResponse])
async def list_anchors(
    entity_type: str,
    entity_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    anchors = await service.list_entity_anchors(db, entity_type, entity_id)
    return [AnchorResponse.model_validate(a) for a in anchors]


@router.post("/batch-submit")
async def batch_submit(
    current_user: CurrentUser = Depends(require_permission("manage", "admin")),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger batch anchor submission (normally done by Celery)."""
    return await service.batch_submit(db)


@router.get("/audit-report")
async def audit_report(
    current_user: CurrentUser = Depends(require_permission("view", "admin")),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    from app.models.blockchain import BlockchainAnchor
    result = await db.execute(
        select(BlockchainAnchor)
        .where(BlockchainAnchor.org_id == current_user.org_id, BlockchainAnchor.is_deleted == False)
        .order_by(BlockchainAnchor.created_at.desc())
        .limit(200)
    )
    anchors = result.scalars().all()
    return {
        "total": len(anchors),
        "anchored": sum(1 for a in anchors if a.status == "anchored"),
        "pending": sum(1 for a in anchors if a.status == "pending"),
        "items": [AnchorResponse.model_validate(a) for a in anchors],
    }
