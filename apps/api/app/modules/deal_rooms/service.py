"""Deal room service — CRUD, membership, documents, activity."""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.deal_rooms import DealRoom, DealRoomActivity, DealRoomDocument, DealRoomMember, DealRoomMessage

logger = structlog.get_logger()

_DEFAULT_PERMISSIONS = {
    "owner": {"can_upload": True, "can_download": True, "can_comment": True, "can_view_financials": True, "can_invite": True},
    "admin": {"can_upload": True, "can_download": True, "can_comment": True, "can_view_financials": True, "can_invite": True},
    "member": {"can_upload": True, "can_download": True, "can_comment": True, "can_view_financials": False, "can_invite": False},
    "viewer": {"can_upload": False, "can_download": False, "can_comment": True, "can_view_financials": False, "can_invite": False},
}


async def create_room(db: AsyncSession, org_id: uuid.UUID, user_id: uuid.UUID, body: Any) -> DealRoom:
    room = DealRoom(
        org_id=org_id,
        project_id=body.project_id,
        name=body.name,
        created_by=user_id,
        settings=body.settings or {},
    )
    db.add(room)
    await db.flush()

    # Add creator as owner
    member = DealRoomMember(
        room_id=room.id,
        user_id=user_id,
        role="owner",
        permissions=_DEFAULT_PERMISSIONS["owner"],
        invited_at=datetime.utcnow(),
        joined_at=datetime.utcnow(),
    )
    db.add(member)
    await log_activity(db, room.id, user_id, "room_created", description=f"Deal room '{room.name}' created")
    await db.commit()
    await db.refresh(room)
    return room


async def get_room(db: AsyncSession, room_id: uuid.UUID, org_id: uuid.UUID) -> DealRoom | None:
    result = await db.execute(
        select(DealRoom)
        .where(DealRoom.id == room_id, DealRoom.org_id == org_id, DealRoom.is_deleted == False)
        .options(selectinload(DealRoom.members))  # type: ignore[attr-defined]
    )
    return result.scalar_one_or_none()


async def list_rooms(db: AsyncSession, org_id: uuid.UUID) -> list[DealRoom]:
    result = await db.execute(
        select(DealRoom).where(DealRoom.org_id == org_id, DealRoom.is_deleted == False)
        .order_by(DealRoom.created_at.desc())
    )
    return list(result.scalars().all())


async def invite_member(
    db: AsyncSession, room_id: uuid.UUID, invited_by: uuid.UUID, body: Any
) -> DealRoomMember:
    permissions = body.permissions or _DEFAULT_PERMISSIONS.get(body.role, _DEFAULT_PERMISSIONS["member"])
    token = secrets.token_urlsafe(32)
    member = DealRoomMember(
        room_id=room_id,
        email=body.email,
        role=body.role,
        org_name=body.org_name,
        permissions=permissions,
        invited_at=datetime.utcnow(),
        invite_token=token,
    )
    db.add(member)
    await log_activity(db, room_id, invited_by, "member_invited", description=f"Invited {body.email} as {body.role}")
    await db.commit()
    await db.refresh(member)
    return member


async def accept_invite(db: AsyncSession, token: str, user_id: uuid.UUID) -> DealRoomMember | None:
    result = await db.execute(select(DealRoomMember).where(DealRoomMember.invite_token == token))
    member = result.scalar_one_or_none()
    if member:
        member.user_id = user_id
        member.joined_at = datetime.utcnow()
        member.invite_token = None
        await log_activity(db, member.room_id, user_id, "member_joined", description="Member joined room")
        await db.commit()
        await db.refresh(member)
    return member


async def share_document(
    db: AsyncSession, room_id: uuid.UUID, document_id: uuid.UUID, shared_by: uuid.UUID
) -> DealRoomDocument:
    doc = DealRoomDocument(room_id=room_id, document_id=document_id, shared_by=shared_by)
    db.add(doc)
    await log_activity(db, room_id, shared_by, "doc_shared", entity_type="document", entity_id=document_id)
    await db.commit()
    await db.refresh(doc)
    return doc


async def send_message(
    db: AsyncSession, room_id: uuid.UUID, user_id: uuid.UUID, body: Any
) -> DealRoomMessage:
    msg = DealRoomMessage(
        room_id=room_id,
        user_id=user_id,
        parent_id=body.parent_id,
        content=body.content,
        mentions=[str(m) for m in (body.mentions or [])],
    )
    db.add(msg)
    await log_activity(db, room_id, user_id, "message", description=body.content[:100])
    await db.commit()
    await db.refresh(msg)
    return msg


async def get_activity_feed(db: AsyncSession, room_id: uuid.UUID, limit: int = 50) -> list[DealRoomActivity]:
    result = await db.execute(
        select(DealRoomActivity)
        .where(DealRoomActivity.room_id == room_id)
        .order_by(DealRoomActivity.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_messages(db: AsyncSession, room_id: uuid.UUID) -> list[DealRoomMessage]:
    result = await db.execute(
        select(DealRoomMessage)
        .where(DealRoomMessage.room_id == room_id, DealRoomMessage.is_deleted == False)
        .order_by(DealRoomMessage.created_at)
    )
    return list(result.scalars().all())


async def close_room(db: AsyncSession, room: DealRoom, closed_by: uuid.UUID) -> DealRoom:
    room.status = "closed"
    await log_activity(db, room.id, closed_by, "room_closed", description="Room closed")
    await db.commit()
    await db.refresh(room)
    return room


async def log_activity(
    db: AsyncSession,
    room_id: uuid.UUID,
    user_id: uuid.UUID,
    activity_type: str,
    entity_type: str | None = None,
    entity_id: uuid.UUID | None = None,
    description: str | None = None,
) -> None:
    activity = DealRoomActivity(
        room_id=room_id,
        user_id=user_id,
        activity_type=activity_type,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )
    db.add(activity)
