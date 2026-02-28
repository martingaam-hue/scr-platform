"""Warm Introductions API router."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.modules.warm_intros import service
from app.modules.warm_intros.schemas import (
    ConnectionCreateRequest,
    ConnectionResponse,
    ConnectionUpdateRequest,
    IntroPathResponse,
    IntroRequestCreateRequest,
    IntroRequestResponse,
    IntroRequestStatusUpdateRequest,
    PathsResponse,
    SuggestionsResponse,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/warm-intros", tags=["warm-introductions"])


# ── Helpers ───────────────────────────────────────────────────────────────────


def _conn_to_response(conn) -> ConnectionResponse:
    return ConnectionResponse(
        id=conn.id,
        user_id=conn.user_id,
        org_id=conn.org_id,
        connection_type=conn.connection_type,
        connected_org_name=conn.connected_org_name,
        connected_person_name=conn.connected_person_name,
        connected_person_email=conn.connected_person_email,
        relationship_strength=conn.relationship_strength,
        last_interaction_date=conn.last_interaction_date,
        notes=conn.notes,
        created_at=conn.created_at,
        updated_at=conn.updated_at,
    )


# ── Connections ───────────────────────────────────────────────────────────────


@router.get("/connections", response_model=list[ConnectionResponse])
async def list_connections(
    current_user: CurrentUser = Depends(require_permission("view", "warm_intro")),
    db: AsyncSession = Depends(get_db),
):
    """List all professional connections for the current user."""
    connections = await service.get_connections(
        db, current_user.user_id, current_user.org_id
    )
    return [_conn_to_response(c) for c in connections]


@router.post(
    "/connections",
    response_model=ConnectionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_connection(
    body: ConnectionCreateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "warm_intro")),
    db: AsyncSession = Depends(get_db),
):
    """Add a new professional connection."""
    try:
        conn = await service.create_connection(
            db, current_user.user_id, current_user.org_id, body
        )
        await db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _conn_to_response(conn)


@router.put("/connections/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: uuid.UUID,
    body: ConnectionUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "warm_intro")),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing professional connection."""
    try:
        conn = await service.update_connection(
            db, current_user.user_id, current_user.org_id, connection_id, body
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _conn_to_response(conn)


@router.delete(
    "/connections/{connection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_connection(
    connection_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("create", "warm_intro")),
    db: AsyncSession = Depends(get_db),
):
    """Delete (soft-delete) a professional connection."""
    try:
        await service.delete_connection(
            db, current_user.user_id, current_user.org_id, connection_id
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


# ── Introduction paths ────────────────────────────────────────────────────────


@router.get("/paths/{investor_id}", response_model=PathsResponse)
async def get_introduction_paths(
    investor_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "warm_intro")),
    db: AsyncSession = Depends(get_db),
):
    """Find warm introduction paths between the current user and an investor."""
    paths = await service.find_introduction_paths(
        db, current_user.user_id, current_user.org_id, investor_id
    )
    return PathsResponse(investor_id=investor_id, paths=paths)


@router.get("/suggestions/{project_id}", response_model=SuggestionsResponse)
async def get_warm_intro_suggestions(
    project_id: uuid.UUID,
    limit: int = Query(10, ge=1, le=50),
    current_user: CurrentUser = Depends(require_permission("view", "warm_intro")),
    db: AsyncSession = Depends(get_db),
):
    """Get warm introduction suggestions for a project, sorted by warmth score."""
    suggestions = await service.suggest_warm_intros(
        db, project_id, current_user.org_id, current_user.user_id, limit=limit
    )
    return SuggestionsResponse(
        project_id=project_id, items=suggestions, total=len(suggestions)
    )


# ── Introduction requests ─────────────────────────────────────────────────────


@router.post(
    "/requests",
    response_model=IntroRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_introduction_request(
    body: IntroRequestCreateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "warm_intro")),
    db: AsyncSession = Depends(get_db),
):
    """Request a warm introduction to an investor."""
    req = await service.request_introduction(
        db,
        requester_id=current_user.user_id,
        requester_org_id=current_user.org_id,
        target_investor_id=body.target_investor_id,
        project_id=body.project_id,
        path=body.path,
        message=body.message,
    )
    await db.commit()
    return service._intro_request_to_response(req)


@router.get("/requests", response_model=list[IntroRequestResponse])
async def list_introduction_requests(
    current_user: CurrentUser = Depends(require_permission("view", "warm_intro")),
    db: AsyncSession = Depends(get_db),
):
    """List all introduction requests made by the current user."""
    requests = await service.list_introduction_requests(
        db, current_user.user_id, current_user.org_id
    )
    return [service._intro_request_to_response(r) for r in requests]


@router.put("/requests/{request_id}/status", response_model=IntroRequestResponse)
async def update_introduction_request_status(
    request_id: uuid.UUID,
    body: IntroRequestStatusUpdateRequest,
    current_user: CurrentUser = Depends(require_permission("create", "warm_intro")),
    db: AsyncSession = Depends(get_db),
):
    """Update introduction request status (connector accepts or declines)."""
    try:
        req = await service.update_request_status(
            db, current_user.org_id, request_id, body.status
        )
        await db.commit()
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return service._intro_request_to_response(req)
