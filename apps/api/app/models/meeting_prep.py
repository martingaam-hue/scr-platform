"""Meeting Prep model — AI-generated briefing documents for investor meetings."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class MeetingBriefing(BaseModel):
    """AI-generated briefing for an investor meeting on a specific project."""

    __tablename__ = "meeting_briefings"

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    meeting_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # screening | dd_review | follow_up | ic_presentation

    meeting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    previous_meeting_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # AI-generated structured briefing
    # {executive_summary, key_metrics, risk_flags, dd_progress,
    #  talking_points, questions_to_ask, changes_since_last}
    briefing_content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # User-edited overrides (applied on top of AI content at read time)
    custom_overrides: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
