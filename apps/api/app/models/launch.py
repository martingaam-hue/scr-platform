"""SQLAlchemy models for E04 Launch Preparation features."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import ModelMixin


class FeatureFlag(Base, ModelMixin):
    """Global feature flag definition."""

    __tablename__ = "feature_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled_globally: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    rollout_pct: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default="100"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="now()"
    )


class FeatureFlagOverride(Base, ModelMixin):
    """Per-org override for a feature flag."""

    __tablename__ = "feature_flag_overrides"
    __table_args__ = (
        UniqueConstraint("flag_name", "org_id", name="uq_flag_override_org"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    flag_name: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("feature_flags.name", ondelete="CASCADE"),
        nullable=False,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="now()"
    )


class UsageEvent(Base, ModelMixin):
    """Append-only usage event per org/user."""

    __tablename__ = "usage_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_metadata: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="now()"
    )


class WaitlistEntry(Base, ModelMixin):
    """Waitlist entry for new signups before full launch."""

    __tablename__ = "waitlist_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    use_case: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="'pending'"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default="now()"
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
