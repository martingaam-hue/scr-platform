"""Collaborative deal rooms API router."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_permission
from app.core.database import get_db
from app.modules.deal_rooms import service
from app.modules.deal_rooms.schemas import (
    ActivityResponse,
    InviteMember,
    MemberResponse,
    MessageResponse,
    RoomCreate,
    RoomResponse,
    SendMessage,
    ShareDocument,
    UpdateMember,
)
from app.schemas.auth import CurrentUser

logger = structlog.get_logger()

router = APIRouter(prefix="/deal-rooms", tags=["deal-rooms"])


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    body: RoomCreate,
    current_user: CurrentUser = Depends(require_permission("manage", "project")),
    db: AsyncSession = Depends(get_db),
):
    room = await service.create_room(db, current_user.org_id, current_user.user_id, body)
    return RoomResponse.model_validate(room)


@router.get("/", response_model=list[RoomResponse])
async def list_rooms(
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    rooms = await service.list_rooms(db, current_user.org_id)
    return [RoomResponse.model_validate(r) for r in rooms]


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    room = await service.get_room(db, room_id, current_user.org_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return RoomResponse.model_validate(room)


@router.post("/{room_id}/invite", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    room_id: uuid.UUID,
    body: InviteMember,
    current_user: CurrentUser = Depends(require_permission("manage", "project")),
    db: AsyncSession = Depends(get_db),
):
    member = await service.invite_member(db, room_id, current_user.user_id, body)
    return MemberResponse.model_validate(member)


@router.post("/{room_id}/documents", status_code=status.HTTP_201_CREATED)
async def share_document(
    room_id: uuid.UUID,
    body: ShareDocument,
    current_user: CurrentUser = Depends(require_permission("manage", "project")),
    db: AsyncSession = Depends(get_db),
):
    doc = await service.share_document(db, room_id, body.document_id, current_user.user_id)
    return {"room_id": str(room_id), "document_id": str(body.document_id)}


@router.get("/{room_id}/activity", response_model=list[ActivityResponse])
async def get_activity(
    room_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    activities = await service.get_activity_feed(db, room_id)
    return [ActivityResponse.model_validate(a) for a in activities]


@router.post("/{room_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    room_id: uuid.UUID,
    body: SendMessage,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    msg = await service.send_message(db, room_id, current_user.user_id, body)
    return MessageResponse.model_validate(msg)


@router.get("/{room_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    room_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("view", "project")),
    db: AsyncSession = Depends(get_db),
):
    messages = await service.get_messages(db, room_id)
    return [MessageResponse.model_validate(m) for m in messages]


@router.post("/{room_id}/close")
async def close_room(
    room_id: uuid.UUID,
    current_user: CurrentUser = Depends(require_permission("manage", "project")),
    db: AsyncSession = Depends(get_db),
):
    room = await service.get_room(db, room_id, current_user.org_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    await service.close_room(db, room, current_user.user_id)
    return {"status": "closed"}
