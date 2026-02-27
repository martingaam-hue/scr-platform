"""Collaboration models: Comment, Activity."""

import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedModel


class Comment(TimestampedModel):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_org_id", "org_id"),
        Index("ix_comments_entity", "entity_type", "entity_id"),
        Index("ix_comments_user_id", "user_id"),
        Index("ix_comments_parent_id", "parent_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    mentions: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_resolved: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, entity_type={self.entity_type!r})>"


class Activity(TimestampedModel):
    __tablename__ = "activities"
    __table_args__ = (
        Index("ix_activities_org_id", "org_id"),
        Index("ix_activities_entity", "entity_type", "entity_id"),
        Index("ix_activities_user_id", "user_id"),
        Index("ix_activities_org_id_created_at", "org_id", "created_at"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
    )
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    def __repr__(self) -> str:
        return f"<Activity(id={self.id}, action={self.action!r}, entity_type={self.entity_type!r})>"
