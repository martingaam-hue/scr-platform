"""Data connectors API router."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.connectors import service
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/connectors", tags=["connectors"])


class EnableRequest(BaseModel):
    api_key: str | None = None
    config: dict[str, Any] | None = None


class ConnectorResponse(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str
    category: str
    description: str | None
    auth_type: str
    pricing_tier: str
    rate_limit_per_minute: int
    documentation_url: str | None
    is_enabled: bool = False
    last_sync_at: Any = None
    total_calls_this_month: int = 0

    class Config:
        from_attributes = True


@router.get("/", response_model=list[ConnectorResponse])
async def list_connectors(
    current_user: CurrentUser = Depends(require_permission("view", "admin")),
    db: AsyncSession = Depends(get_db),
):
    connectors = await service.list_connectors(db)
    org_configs = {c.connector_id: c for c in await service.list_org_configs(db, current_user.org_id)}
    result = []
    for conn in connectors:
        cfg = org_configs.get(conn.id)
        data = conn.to_dict()
        data["is_enabled"] = cfg.is_enabled if cfg else False
        data["last_sync_at"] = cfg.last_sync_at.isoformat() if (cfg and cfg.last_sync_at) else None
        data["total_calls_this_month"] = cfg.total_calls_this_month if cfg else 0
        result.append(ConnectorResponse(**data))
    return result


@router.post("/{connector_id}/enable", status_code=status.HTTP_200_OK)
async def enable_connector(
    connector_id: uuid.UUID,
    body: EnableRequest,
    current_user: CurrentUser = Depends(require_permission("manage", "admin")),
    db: AsyncSession = Depends(get_db),
):
    cfg = await service.enable_connector(db, current_user.org_id, connector_id, body.api_key, body.config)
    return {"status": "enabled", "connector_id": str(connector_id)}


@router.post("/{connector_id}/disable", status_code=status.HTTP_200_OK)
async def disable_connector(
    connector_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("manage", "admin")),
    db: AsyncSession = Depends(get_db),
):
    await service.disable_connector(db, current_user.org_id, connector_id)
    return {"status": "disabled"}


@router.post("/{connector_id}/test")
async def test_connector(
    connector_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("manage", "admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await service.test_connector(db, current_user.org_id, connector_id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


class IngestRequest(BaseModel):
    project_id: uuid.UUID
    endpoint: str
    params: dict[str, Any] | None = None
    folder_id: uuid.UUID | None = None


@router.post("/{connector_id}/ingest", status_code=status.HTTP_201_CREATED)
async def ingest_to_dataroom(
    connector_id: uuid.UUID,
    body: IngestRequest,
    current_user: CurrentUser = Depends(require_permission("upload", "document")),
    db: AsyncSession = Depends(get_db),
):
    """Fetch data from a connector and save it as a JSON document in the dataroom.

    Returns the created document ID so you can navigate to it in the data room.
    """
    try:
        result = await service.ingest_to_dataroom(
            db,
            current_user.org_id,
            current_user.user_id,
            connector_id,
            body.project_id,
            body.endpoint,
            body.params,
            body.folder_id,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/usage")
async def get_usage(
    current_user: CurrentUser = Depends(require_permission("view", "admin")),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_usage_stats(db, current_user.org_id)
