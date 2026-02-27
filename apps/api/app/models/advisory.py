"""Advisory models: BoardAdvisorProfile, BoardAdvisorApplication, InvestorPersona,
EquityScenario, CapitalEfficiencyMetrics, MonitoringAlert, InvestorSignalScore,
InsuranceQuote, InsurancePolicy."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.enums import (
    AdvisorAvailabilityStatus,
    AdvisorCompensationPreference,
    AntiDilutionType,
    BoardAdvisorApplicationStatus,
    EquitySecurityType,
    InsurancePolicyStatus,
    InsurancePremiumFrequency,
    InsuranceSide,
    InvestorPersonaStrategy,
    MonitoringAlertDomain,
    MonitoringAlertSeverity,
    MonitoringAlertType,
)


class BoardAdvisorProfile(BaseModel):
    __tablename__ = "board_advisor_profiles"
    __table_args__ = (
        Index("ix_board_advisor_profiles_user_id", "user_id"),
        Index("ix_board_advisor_profiles_org_id", "org_id"),
        Index("ix_board_advisor_profiles_availability", "availability_status"),
        Index("ix_board_advisor_profiles_verified", "verified"),
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
    expertise_areas: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    industry_experience: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    board_positions_held: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    availability_status: Mapped[AdvisorAvailabilityStatus] = mapped_column(
        nullable=False, default=AdvisorAvailabilityStatus.AVAILABLE
    )
    compensation_preference: Mapped[AdvisorCompensationPreference] = mapped_column(
        nullable=False, default=AdvisorCompensationPreference.NEGOTIABLE
    )
    bio: Mapped[str] = mapped_column(Text, nullable=False, default="")
    linkedin_url: Mapped[str | None] = mapped_column(String(512))
    verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    match_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_rating: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    # Relationships
    applications: Mapped[list["BoardAdvisorApplication"]] = relationship(
        back_populates="advisor_profile"
    )

    def __repr__(self) -> str:
        return f"<BoardAdvisorProfile(id={self.id}, user_id={self.user_id})>"


class BoardAdvisorApplication(BaseModel):
    __tablename__ = "board_advisor_applications"
    __table_args__ = (
        Index("ix_board_advisor_applications_project_id", "project_id"),
        Index("ix_board_advisor_applications_advisor_profile_id", "advisor_profile_id"),
        Index("ix_board_advisor_applications_ally_org_id", "ally_org_id"),
        Index("ix_board_advisor_applications_status", "status"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    advisor_profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("board_advisor_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    ally_org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[BoardAdvisorApplicationStatus] = mapped_column(
        nullable=False, default=BoardAdvisorApplicationStatus.PENDING
    )
    message: Mapped[str | None] = mapped_column(Text)
    role_offered: Mapped[str] = mapped_column(String(500), nullable=False)
    equity_offered: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    compensation_terms: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    signal_score_impact: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    started_at: Mapped[datetime | None] = mapped_column()
    ended_at: Mapped[datetime | None] = mapped_column()

    # Relationships
    advisor_profile: Mapped["BoardAdvisorProfile"] = relationship(
        back_populates="applications"
    )

    def __repr__(self) -> str:
        return f"<BoardAdvisorApplication(id={self.id}, status={self.status.value})>"


class InvestorPersona(BaseModel):
    __tablename__ = "investor_personas"
    __table_args__ = (
        Index("ix_investor_personas_org_id", "org_id"),
        Index("ix_investor_personas_org_id_active", "org_id", "is_active"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    persona_name: Mapped[str] = mapped_column(String(500), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )
    strategy_type: Mapped[InvestorPersonaStrategy] = mapped_column(
        nullable=False, default=InvestorPersonaStrategy.MODERATE
    )
    target_irr_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    target_irr_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    target_moic_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    preferred_asset_types: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    preferred_geographies: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    preferred_stages: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    ticket_size_min: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    ticket_size_max: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    esg_requirements: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    risk_tolerance: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    co_investment_preference: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    fund_structure_preference: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    def __repr__(self) -> str:
        return f"<InvestorPersona(id={self.id}, name={self.persona_name!r})>"


class EquityScenario(BaseModel):
    __tablename__ = "equity_scenarios"
    __table_args__ = (
        Index("ix_equity_scenarios_org_id", "org_id"),
        Index("ix_equity_scenarios_project_id", "project_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
    )
    scenario_name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    pre_money_valuation: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    investment_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    security_type: Mapped[EquitySecurityType] = mapped_column(
        nullable=False, default=EquitySecurityType.COMMON_EQUITY
    )
    equity_percentage: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=False)
    post_money_valuation: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    shares_outstanding_before: Mapped[int] = mapped_column(Integer, nullable=False)
    new_shares_issued: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_share: Mapped[Decimal] = mapped_column(Numeric(19, 6), nullable=False)
    liquidation_preference: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    participation_cap: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    anti_dilution_type: Mapped[AntiDilutionType | None] = mapped_column()
    conversion_terms: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    vesting_schedule: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    cap_table_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    waterfall_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    dilution_impact: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    def __repr__(self) -> str:
        return f"<EquityScenario(id={self.id}, name={self.scenario_name!r})>"


class CapitalEfficiencyMetrics(BaseModel):
    __tablename__ = "capital_efficiency_metrics"
    __table_args__ = (
        Index("ix_capital_efficiency_metrics_org_id", "org_id"),
        Index("ix_capital_efficiency_metrics_portfolio_id", "portfolio_id"),
        Index("ix_capital_efficiency_metrics_period", "org_id", "period_start", "period_end"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="SET NULL"),
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    due_diligence_savings: Mapped[Decimal] = mapped_column(
        Numeric(19, 4), nullable=False, default=0
    )
    legal_automation_savings: Mapped[Decimal] = mapped_column(
        Numeric(19, 4), nullable=False, default=0
    )
    risk_analytics_savings: Mapped[Decimal] = mapped_column(
        Numeric(19, 4), nullable=False, default=0
    )
    tax_credit_value_captured: Mapped[Decimal] = mapped_column(
        Numeric(19, 4), nullable=False, default=0
    )
    time_saved_hours: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    deals_screened: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deals_closed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_time_to_close_days: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    portfolio_irr_improvement: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    industry_avg_dd_cost: Mapped[Decimal] = mapped_column(
        Numeric(19, 4), nullable=False, default=0
    )
    industry_avg_time_to_close: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=0
    )
    platform_efficiency_score: Mapped[Decimal] = mapped_column(
        Numeric(6, 2), nullable=False, default=0
    )
    breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    def __repr__(self) -> str:
        return (
            f"<CapitalEfficiencyMetrics(id={self.id}, org_id={self.org_id}, "
            f"period={self.period_start}–{self.period_end})>"
        )


class MonitoringAlert(BaseModel):
    __tablename__ = "monitoring_alerts"
    __table_args__ = (
        Index("ix_monitoring_alerts_org_id", "org_id"),
        Index("ix_monitoring_alerts_project_id", "project_id"),
        Index("ix_monitoring_alerts_portfolio_id", "portfolio_id"),
        Index("ix_monitoring_alerts_alert_type", "alert_type"),
        Index("ix_monitoring_alerts_severity", "severity"),
        Index("ix_monitoring_alerts_is_read", "org_id", "is_read"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
    )
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="SET NULL"),
    )
    alert_type: Mapped[MonitoringAlertType] = mapped_column(nullable=False)
    severity: Mapped[MonitoringAlertSeverity] = mapped_column(nullable=False)
    domain: Mapped[MonitoringAlertDomain] = mapped_column(nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(1024))
    source_name: Mapped[str | None] = mapped_column(String(255))
    data_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    affected_entities: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    is_actioned: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )
    action_taken: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<MonitoringAlert(id={self.id}, type={self.alert_type.value}, severity={self.severity.value})>"


class InvestorSignalScore(BaseModel):
    __tablename__ = "investor_signal_scores"
    __table_args__ = (
        Index("ix_investor_signal_scores_org_id", "org_id"),
        Index("ix_investor_signal_scores_org_id_calculated", "org_id", "calculated_at"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    overall_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    financial_capacity_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    financial_capacity_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    risk_management_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    risk_management_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    investment_strategy_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    investment_strategy_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    team_experience_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    team_experience_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    esg_commitment_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    esg_commitment_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    platform_readiness_score: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    platform_readiness_details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    gaps: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    recommendations: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    score_factors: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    data_sources: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    calculated_at: Mapped[datetime] = mapped_column(nullable=False)
    previous_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    score_change: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))

    def __repr__(self) -> str:
        return f"<InvestorSignalScore(id={self.id}, org_id={self.org_id}, score={self.overall_score})>"


class InsuranceQuote(BaseModel):
    """Placeholder model for insurance quotes referenced by InsurancePolicy."""

    __tablename__ = "insurance_quotes"
    __table_args__ = (
        Index("ix_insurance_quotes_org_id", "org_id"),
        Index("ix_insurance_quotes_project_id", "project_id"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
    )
    provider_name: Mapped[str] = mapped_column(String(500), nullable=False)
    coverage_type: Mapped[str] = mapped_column(String(255), nullable=False)
    coverage_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    quoted_premium: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD")
    valid_until: Mapped[date | None] = mapped_column(Date)
    terms: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    side: Mapped[InsuranceSide] = mapped_column(
        nullable=False, default=InsuranceSide.INVESTOR
    )

    # Relationships
    policies: Mapped[list["InsurancePolicy"]] = relationship(back_populates="quote")

    def __repr__(self) -> str:
        return f"<InsuranceQuote(id={self.id}, provider={self.provider_name!r})>"


class InsurancePolicy(BaseModel):
    __tablename__ = "insurance_policies"
    __table_args__ = (
        Index("ix_insurance_policies_org_id", "org_id"),
        Index("ix_insurance_policies_quote_id", "quote_id"),
        Index("ix_insurance_policies_project_id", "project_id"),
        Index("ix_insurance_policies_portfolio_id", "portfolio_id"),
        Index("ix_insurance_policies_status", "status"),
    )

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    quote_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("insurance_quotes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="SET NULL"),
    )
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="SET NULL"),
    )
    policy_number: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(500), nullable=False)
    coverage_type: Mapped[str] = mapped_column(String(255), nullable=False)
    coverage_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    premium_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    premium_frequency: Mapped[InsurancePremiumFrequency] = mapped_column(nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[InsurancePolicyStatus] = mapped_column(
        nullable=False, default=InsurancePolicyStatus.ACTIVE
    )
    risk_score_impact: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=0
    )
    terms: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    side: Mapped[InsuranceSide] = mapped_column(
        nullable=False, default=InsuranceSide.INVESTOR
    )

    # Relationships
    quote: Mapped["InsuranceQuote"] = relationship(back_populates="policies")

    def __repr__(self) -> str:
        return f"<InsurancePolicy(id={self.id}, policy_number={self.policy_number!r}, status={self.status.value})>"
