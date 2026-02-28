"""Gamification models — badges, quests, leaderboard opt-in."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TimestampedModel


class Badge(BaseModel):
    """Platform badge definition (seeded, not user-created)."""

    __tablename__ = "badges"

    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(20), nullable=True)  # emoji or icon name
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    # onboarding, data_room, signal_score, matching, certification
    criteria: Mapped[dict] = mapped_column(JSONB, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=10, server_default="10")
    rarity: Mapped[str] = mapped_column(
        String(20), default="common", server_default="common"
    )  # common, uncommon, rare, epic, legendary


class UserBadge(TimestampedModel):
    """Record of a badge earned by a user, optionally scoped to a project."""

    __tablename__ = "user_badges"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    badge_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("badges.id", ondelete="CASCADE"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "project_id", "badge_id", name="uq_user_project_badge"),
    )


class ImprovementQuest(BaseModel):
    """AI-generated improvement quest for a specific project."""

    __tablename__ = "improvement_quests"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # upload_document, complete_section, add_team_member, improve_dimension
    target_dimension: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estimated_score_impact: Mapped[int] = mapped_column(Integer, default=0)
    reward_badge_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("badges.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default="active", server_default="active"
    )  # active, completed, expired
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
