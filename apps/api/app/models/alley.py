"""Alley-side models — risk mitigation tracking."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedModel


class RiskMitigationStatus(TimestampedModel):
    """Tracks a project holder's mitigation progress on a specific risk item."""
    __tablename__ = "risk_mitigation_statuses"

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    risk_item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="unaddressed"
    )  # acknowledged | in_progress | mitigated | accepted | unaddressed
    evidence_document_ids: Mapped[list[uuid.UUID] | None] = mapped_column(ARRAY(UUID(as_uuid=True)))
    notes: Mapped[str | None] = mapped_column(String(2000))
    guidance: Mapped[str | None] = mapped_column(String(2000))
