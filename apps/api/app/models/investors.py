"""Investor models: Portfolio, PortfolioHolding, PortfolioMetrics, InvestorMandate, RiskAssessment."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, TimestampedModel
from app.models.enums import (
    AssetType,
    FundType,
    HoldingStatus,
    PortfolioStatus,
    PortfolioStrategy,
    RiskAssessmentStatus,
    RiskEntityType,
    RiskProbability,
    RiskSeverity,
    RiskTolerance,
    RiskType,
    SFDRClassification,
)


class Portfolio(BaseModel):
    __tablename__ = "portfolios"
    __table_args__ = (
        Index("ix_portfolios_org_id", "org_id"),
        Index("ix_portfolios_org_id_status", "org_id", "status"),
        Index("ix_portfolios_status", "status"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    strategy: Mapped[PortfolioStrategy] = mapped_column(nullable=False)
    fund_type: Mapped[FundType] = mapped_column(nullable=False)
    vintage_year: Mapped[int | None] = mapped_column(Integer)
    target_aum: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    current_aum: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    sfdr_classification: Mapped[SFDRClassification] = mapped_column(
        nullable=False, default=SFDRClassification.NOT_APPLICABLE
    )
    status: Mapped[PortfolioStatus] = mapped_column(
        nullable=False, default=PortfolioStatus.FUNDRAISING
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="portfolios"
    )
    holdings: Mapped[list["PortfolioHolding"]] = relationship(back_populates="portfolio")
    metrics: Mapped[list["PortfolioMetrics"]] = relationship(back_populates="portfolio")

    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, name={self.name!r}, status={self.status.value})>"


class PortfolioHolding(BaseModel):
    __tablename__ = "portfolio_holdings"
    __table_args__ = (
        Index("ix_portfolio_holdings_portfolio_id", "portfolio_id"),
        Index("ix_portfolio_holdings_project_id", "project_id"),
        Index("ix_portfolio_holdings_status", "status"),
        Index("ix_portfolio_holdings_portfolio_id_status", "portfolio_id", "status"),
    )

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
    )
    asset_name: Mapped[str] = mapped_column(String(500), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(nullable=False)
    investment_date: Mapped[date] = mapped_column(Date, nullable=False)
    investment_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    current_value: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    ownership_pct: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    status: Mapped[HoldingStatus] = mapped_column(
        nullable=False, default=HoldingStatus.ACTIVE
    )
    exit_date: Mapped[date | None] = mapped_column(Date)
    exit_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship(back_populates="holdings")

    def __repr__(self) -> str:
        return f"<PortfolioHolding(id={self.id}, asset_name={self.asset_name!r})>"


class PortfolioMetrics(TimestampedModel):
    __tablename__ = "portfolio_metrics"
    __table_args__ = (
        Index("ix_portfolio_metrics_portfolio_id", "portfolio_id"),
        Index("ix_portfolio_metrics_as_of_date", "portfolio_id", "as_of_date"),
    )

    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    irr_gross: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    irr_net: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    moic: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    tvpi: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    dpi: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    rvpi: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    total_invested: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    total_distributions: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    cash_flows: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    esg_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    carbon_reduction_tons: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Relationships
    portfolio: Mapped["Portfolio"] = relationship(back_populates="metrics")


class InvestorMandate(BaseModel):
    __tablename__ = "investor_mandates"
    __table_args__ = (
        Index("ix_investor_mandates_org_id", "org_id"),
        Index("ix_investor_mandates_is_active", "org_id", "is_active"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    sectors: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    geographies: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    stages: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    ticket_size_min: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    ticket_size_max: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    target_irr_min: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    risk_tolerance: Mapped[RiskTolerance] = mapped_column(
        nullable=False, default=RiskTolerance.MODERATE
    )
    esg_requirements: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    exclusions: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true", nullable=False)

    def __repr__(self) -> str:
        return f"<InvestorMandate(id={self.id}, name={self.name!r})>"


class RiskAssessment(BaseModel):
    __tablename__ = "risk_assessments"
    __table_args__ = (
        Index("ix_risk_assessments_org_id", "org_id"),
        Index("ix_risk_assessments_entity", "entity_type", "entity_id"),
        Index("ix_risk_assessments_risk_type", "risk_type"),
        Index("ix_risk_assessments_severity", "severity"),
    )

    entity_type: Mapped[RiskEntityType] = mapped_column(nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    risk_type: Mapped[RiskType] = mapped_column(nullable=False)
    severity: Mapped[RiskSeverity] = mapped_column(nullable=False)
    probability: Mapped[RiskProbability] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    mitigation: Mapped[str | None] = mapped_column(Text)
    status: Mapped[RiskAssessmentStatus] = mapped_column(
        nullable=False, default=RiskAssessmentStatus.IDENTIFIED
    )
    assessed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False,
    )
