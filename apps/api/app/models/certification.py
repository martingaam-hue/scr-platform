"""Investor Readiness Certification model."""

from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class InvestorReadinessCertification(BaseModel):
    __tablename__ = "investor_readiness_certifications"
    __table_args__ = (
        UniqueConstraint("project_id", name="uq_certification_project"),
        Index("ix_certification_org_status", "org_id", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_certified", server_default="not_certified"
    )
    # not_certified | certified | suspended | revoked
    certified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    suspended_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    certification_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dimension_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tier: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # standard (80-89) | premium (90-95) | elite (96-100)
    certification_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    consecutive_months_certified: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
