"""Collaboration Pydantic schemas: comments, activity."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ── Comment schemas ─────────────────────────────────────────────────────────


class CreateCommentRequest(BaseModel):
    entity_type: str = Field(min_length=1, max_length=100)
    entity_id: uuid.UUID
    content: str = Field(min_length=1)
    parent_comment_id: uuid.UUID | None = None


class UpdateCommentRequest(BaseModel):
    content: str = Field(min_length=1)


class CommentAuthor(BaseModel):
    user_id: uuid.UUID
    full_name: str
    avatar_url: str | None = None


class CommentResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    user_id: uuid.UUID
    author: CommentAuthor
    entity_type: str
    entity_id: uuid.UUID
    parent_id: uuid.UUID | None
    content: str
    mentions: dict[str, Any] | None
    is_resolved: bool
    created_at: datetime
    replies: list["CommentResponse"] = Field(default_factory=list)


class CommentListResponse(BaseModel):
    items: list[CommentResponse]
    total: int


# ── Activity schemas ────────────────────────────────────────────────────────


class ActivityResponse(BaseModel):
    id: uuid.UUID
    org_id: uuid.UUID
    user_id: uuid.UUID | None
    user_name: str | None = None
    user_avatar: str | None = None
    entity_type: str
    entity_id: uuid.UUID
    action: str
    description: str
    changes: dict[str, Any] | None
    created_at: datetime


class ActivityListResponse(BaseModel):
    items: list[ActivityResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
