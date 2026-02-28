"""Deal Room Pydantic schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RoomCreate(BaseModel):
    project_id: uuid.UUID
    name: str
    settings: dict[str, Any] | None = None


class InviteMember(BaseModel):
    email: str
    role: str = "member"  # owner, admin, member, viewer
    org_name: str | None = None
    permissions: dict[str, bool] | None = None


class UpdateMember(BaseModel):
    role: str | None = None
    permissions: dict[str, bool] | None = None


class ShareDocument(BaseModel):
    document_id: uuid.UUID


class SendMessage(BaseModel):
    content: str
    parent_id: uuid.UUID | None = None
    mentions: list[uuid.UUID] | None = None


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    room_id: uuid.UUID
    user_id: uuid.UUID | None
    email: str | None
    role: str
    org_name: str | None
    permissions: dict[str, Any]
    invited_at: datetime
    joined_at: datetime | None
    nda_signed_at: datetime | None


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    room_id: uuid.UUID
    user_id: uuid.UUID
    parent_id: uuid.UUID | None
    content: str
    mentions: list[Any]
    created_at: datetime


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    room_id: uuid.UUID
    user_id: uuid.UUID
    activity_type: str
    entity_type: str | None
    entity_id: uuid.UUID | None
    description: str | None
    created_at: datetime


class RoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    org_id: uuid.UUID
    project_id: uuid.UUID
    name: str
    status: str
    created_by: uuid.UUID
    settings: dict[str, Any]
    created_at: datetime
    members: list[MemberResponse] = []
