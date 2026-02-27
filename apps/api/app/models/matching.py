"""Matching models: MatchResult, MatchMessage."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TimestampedModel
from app.models.enums import MatchInitiator, MatchStatus


class MatchResult(BaseModel):
    __tablename__ = "match_results"
    __table_args__ = (
        Index("ix_match_results_investor_org_id", "investor_org_id"),
        Index("ix_match_results_ally_org_id", "ally_org_id"),
        Index("ix_match_results_project_id", "project_id"),
        Index("ix_match_results_status", "status"),
        Index("ix_match_results_investor_status", "investor_org_id", "status"),
        Index("ix_match_results_ally_status", "ally_org_id", "status"),
    )

    investor_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    ally_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    mandate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("investor_mandates.id", ondelete="SET NULL"),
    )
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    score_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[MatchStatus] = mapped_column(
        nullable=False, default=MatchStatus.SUGGESTED
    )
    initiated_by: Mapped[MatchInitiator] = mapped_column(
        nullable=False, default=MatchInitiator.SYSTEM
    )
    investor_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ally_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Relationships
    investor_org: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        foreign_keys=[investor_org_id],
    )
    ally_org: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        foreign_keys=[ally_org_id],
    )
    messages: Mapped[list["MatchMessage"]] = relationship(back_populates="match_result")

    def __repr__(self) -> str:
        return f"<MatchResult(id={self.id}, score={self.overall_score}, status={self.status.value})>"


class MatchMessage(TimestampedModel):
    __tablename__ = "match_messages"
    __table_args__ = (
        Index("ix_match_messages_match_id", "match_id"),
        Index("ix_match_messages_sender_id", "sender_id"),
    )

    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("match_results.id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_system: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )

    # Relationships
    match_result: Mapped["MatchResult"] = relationship(back_populates="messages")
