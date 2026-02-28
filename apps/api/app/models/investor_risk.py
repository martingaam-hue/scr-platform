"""InvestorRiskProfile model."""

import uuid
from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedModel


class InvestorRiskProfile(TimestampedModel):
    __tablename__ = "investor_risk_profiles"
    __table_args__ = (
        Index("ix_investor_risk_profiles_user_id", "user_id"),
        Index("ix_investor_risk_profiles_org_id", "org_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Assessment answers
    experience_level: Mapped[str] = mapped_column(String(50), nullable=False)
    investment_horizon_years: Mapped[int] = mapped_column(Integer, nullable=False)
    loss_tolerance_percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    liquidity_needs: Mapped[str] = mapped_column(String(20), nullable=False)
    concentration_max_percentage: Mapped[int] = mapped_column(Integer, nullable=False)
    max_drawdown_tolerance: Mapped[int] = mapped_column(Integer, nullable=False)

    # Calculated scores (deterministic)
    sophistication_score: Mapped[float] = mapped_column(nullable=False)
    risk_appetite_score: Mapped[float] = mapped_column(nullable=False)
    risk_category: Mapped[str] = mapped_column(String(20), nullable=False)

    # Recommended allocation percentages
    recommended_allocation: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
