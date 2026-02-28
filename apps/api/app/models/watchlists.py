"""AI Watchlist and alert models for proactive deal discovery."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, TimestampedModel


class Watchlist(BaseModel):
    """User-configured monitoring criteria that generates alerts."""

    __tablename__ = "watchlists"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    watch_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # new_projects, score_changes, risk_alerts, market_events, specific_project
    criteria: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structured filters or {project_id: "..."} for specific project watch
    alert_channels: Mapped[list] = mapped_column(JSONB, default=list)  # ["in_app", "email"]
    alert_frequency: Mapped[str] = mapped_column(
        String(20), default="immediate", server_default="immediate"
    )  # immediate, daily_digest, weekly
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_checked_at: Mapped[uuid.UUID | None] = mapped_column(
        JSONB, nullable=True
    )  # stored as ISO string in JSONB for simplicity
    total_alerts_sent: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class WatchlistAlert(TimestampedModel):
    """Generated alert from a watchlist match."""

    __tablename__ = "watchlist_alerts"

    watchlist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # new_match, score_improved, score_declined, risk_flag, market_event
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    data: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    __table_args__ = (
        Index("ix_watchlist_alert_user_created", "user_id", "created_at"),
    )
