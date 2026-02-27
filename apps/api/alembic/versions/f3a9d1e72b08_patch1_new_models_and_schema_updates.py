"""patch1: new advisory models + signal_score/risk_assessment updates

Revision ID: f3a9d1e72b08
Revises: cb877e7100cf
Create Date: 2026-02-27 12:00:00.000000

Changes:
  - CREATE: board_advisor_profiles
  - CREATE: board_advisor_applications
  - CREATE: investor_personas
  - CREATE: equity_scenarios
  - CREATE: capital_efficiency_metrics
  - CREATE: monitoring_alerts
  - CREATE: investor_signal_scores
  - CREATE: insurance_quotes
  - CREATE: insurance_policies
  - ALTER:  signal_scores — rename 4 dimension columns, add 6th dimension + 4 new fields
  - ALTER:  risk_assessments — add 5-domain scores + monitoring fields
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "f3a9d1e72b08"
down_revision: Union[str, None] = "cb877e7100cf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Enum helpers ──────────────────────────────────────────────────────────────

def _create_enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name)


def upgrade() -> None:
    conn = op.get_bind()

    # ── New PostgreSQL enums ───────────────────────────────────────────────────

    _create_enum(
        "advisoravailabilitystatus", "available", "limited", "unavailable"
    ).create(conn, checkfirst=True)

    _create_enum(
        "advisorcompensationpreference", "equity", "cash", "pro_bono", "negotiable"
    ).create(conn, checkfirst=True)

    _create_enum(
        "boardadvisorapplicationstatus",
        "pending", "accepted", "rejected", "withdrawn", "active", "completed",
    ).create(conn, checkfirst=True)

    _create_enum(
        "investorpersonastrategy",
        "conservative", "moderate", "growth", "aggressive", "impact_first",
    ).create(conn, checkfirst=True)

    _create_enum(
        "equitysecuritytype",
        "common_equity", "preferred_equity", "convertible_note", "safe", "revenue_share",
    ).create(conn, checkfirst=True)

    _create_enum(
        "antidilutiontype", "none", "broad_based", "narrow_based", "full_ratchet"
    ).create(conn, checkfirst=True)

    _create_enum(
        "monitoringalerttype",
        "regulatory_change", "market_shift", "risk_threshold",
        "data_update", "news_alert", "compliance_deadline",
    ).create(conn, checkfirst=True)

    _create_enum(
        "monitoringalertseverity", "info", "warning", "critical"
    ).create(conn, checkfirst=True)

    _create_enum(
        "monitoringalertdomain", "market", "climate", "regulatory", "technology", "liquidity"
    ).create(conn, checkfirst=True)

    _create_enum(
        "insurancepremiumfrequency", "monthly", "quarterly", "annual"
    ).create(conn, checkfirst=True)

    _create_enum(
        "insurancepolicystatus", "active", "expired", "cancelled", "pending_renewal"
    ).create(conn, checkfirst=True)

    _create_enum(
        "insuranceside", "ally", "investor"
    ).create(conn, checkfirst=True)

    # ── board_advisor_profiles ────────────────────────────────────────────────

    op.create_table(
        "board_advisor_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expertise_areas", postgresql.JSONB(), nullable=True),
        sa.Column("industry_experience", postgresql.JSONB(), nullable=True),
        sa.Column("board_positions_held", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "availability_status",
            postgresql.ENUM("available", "limited", "unavailable",
                            name="advisoravailabilitystatus", create_type=False),
            nullable=False,
            server_default="available",
        ),
        sa.Column(
            "compensation_preference",
            postgresql.ENUM("equity", "cash", "pro_bono", "negotiable",
                            name="advisorcompensationpreference", create_type=False),
            nullable=False,
            server_default="negotiable",
        ),
        sa.Column("bio", sa.Text(), nullable=False, server_default=""),
        sa.Column("linkedin_url", sa.String(512), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("match_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_rating", sa.Numeric(4, 2), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_board_advisor_profiles_user_id", "board_advisor_profiles", ["user_id"])
    op.create_index("ix_board_advisor_profiles_org_id", "board_advisor_profiles", ["org_id"])
    op.create_index("ix_board_advisor_profiles_availability", "board_advisor_profiles", ["availability_status"])
    op.create_index("ix_board_advisor_profiles_verified", "board_advisor_profiles", ["verified"])

    # ── board_advisor_applications ────────────────────────────────────────────

    op.create_table(
        "board_advisor_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("advisor_profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ally_org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "pending", "accepted", "rejected", "withdrawn", "active", "completed",
                name="boardadvisorapplicationstatus", create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("role_offered", sa.String(500), nullable=False),
        sa.Column("equity_offered", sa.Numeric(10, 4), nullable=True),
        sa.Column("compensation_terms", postgresql.JSONB(), nullable=True),
        sa.Column("signal_score_impact", sa.Numeric(10, 4), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["advisor_profile_id"], ["board_advisor_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ally_org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_board_advisor_applications_project_id", "board_advisor_applications", ["project_id"])
    op.create_index("ix_board_advisor_applications_advisor_profile_id", "board_advisor_applications", ["advisor_profile_id"])
    op.create_index("ix_board_advisor_applications_ally_org_id", "board_advisor_applications", ["ally_org_id"])
    op.create_index("ix_board_advisor_applications_status", "board_advisor_applications", ["status"])

    # ── investor_personas ─────────────────────────────────────────────────────

    op.create_table(
        "investor_personas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("persona_name", sa.String(500), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "strategy_type",
            postgresql.ENUM(
                "conservative", "moderate", "growth", "aggressive", "impact_first",
                name="investorpersonastrategy", create_type=False,
            ),
            nullable=False,
            server_default="moderate",
        ),
        sa.Column("target_irr_min", sa.Numeric(10, 4), nullable=True),
        sa.Column("target_irr_max", sa.Numeric(10, 4), nullable=True),
        sa.Column("target_moic_min", sa.Numeric(10, 4), nullable=True),
        sa.Column("preferred_asset_types", postgresql.JSONB(), nullable=True),
        sa.Column("preferred_geographies", postgresql.JSONB(), nullable=True),
        sa.Column("preferred_stages", postgresql.JSONB(), nullable=True),
        sa.Column("ticket_size_min", sa.Numeric(19, 4), nullable=True),
        sa.Column("ticket_size_max", sa.Numeric(19, 4), nullable=True),
        sa.Column("esg_requirements", postgresql.JSONB(), nullable=True),
        sa.Column("risk_tolerance", postgresql.JSONB(), nullable=True),
        sa.Column("co_investment_preference", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("fund_structure_preference", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_investor_personas_org_id", "investor_personas", ["org_id"])
    op.create_index("ix_investor_personas_org_id_active", "investor_personas", ["org_id", "is_active"])

    # ── equity_scenarios ──────────────────────────────────────────────────────

    op.create_table(
        "equity_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scenario_name", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pre_money_valuation", sa.Numeric(19, 4), nullable=False),
        sa.Column("investment_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column(
            "security_type",
            postgresql.ENUM(
                "common_equity", "preferred_equity", "convertible_note", "safe", "revenue_share",
                name="equitysecuritytype", create_type=False,
            ),
            nullable=False,
            server_default="common_equity",
        ),
        sa.Column("equity_percentage", sa.Numeric(10, 6), nullable=False),
        sa.Column("post_money_valuation", sa.Numeric(19, 4), nullable=False),
        sa.Column("shares_outstanding_before", sa.Integer(), nullable=False),
        sa.Column("new_shares_issued", sa.Integer(), nullable=False),
        sa.Column("price_per_share", sa.Numeric(19, 6), nullable=False),
        sa.Column("liquidation_preference", sa.Numeric(19, 4), nullable=True),
        sa.Column("participation_cap", sa.Numeric(19, 4), nullable=True),
        sa.Column(
            "anti_dilution_type",
            postgresql.ENUM(
                "none", "broad_based", "narrow_based", "full_ratchet",
                name="antidilutiontype", create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("conversion_terms", postgresql.JSONB(), nullable=True),
        sa.Column("vesting_schedule", postgresql.JSONB(), nullable=True),
        sa.Column("cap_table_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("waterfall_analysis", postgresql.JSONB(), nullable=True),
        sa.Column("dilution_impact", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_equity_scenarios_org_id", "equity_scenarios", ["org_id"])
    op.create_index("ix_equity_scenarios_project_id", "equity_scenarios", ["project_id"])

    # ── capital_efficiency_metrics ────────────────────────────────────────────

    op.create_table(
        "capital_efficiency_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("due_diligence_savings", sa.Numeric(19, 4), nullable=False, server_default="0"),
        sa.Column("legal_automation_savings", sa.Numeric(19, 4), nullable=False, server_default="0"),
        sa.Column("risk_analytics_savings", sa.Numeric(19, 4), nullable=False, server_default="0"),
        sa.Column("tax_credit_value_captured", sa.Numeric(19, 4), nullable=False, server_default="0"),
        sa.Column("time_saved_hours", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("deals_screened", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deals_closed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_time_to_close_days", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("portfolio_irr_improvement", sa.Numeric(10, 4), nullable=True),
        sa.Column("industry_avg_dd_cost", sa.Numeric(19, 4), nullable=False, server_default="0"),
        sa.Column("industry_avg_time_to_close", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("platform_efficiency_score", sa.Numeric(6, 2), nullable=False, server_default="0"),
        sa.Column("breakdown", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_capital_efficiency_metrics_org_id", "capital_efficiency_metrics", ["org_id"])
    op.create_index("ix_capital_efficiency_metrics_portfolio_id", "capital_efficiency_metrics", ["portfolio_id"])
    op.create_index("ix_capital_efficiency_metrics_period", "capital_efficiency_metrics",
                    ["org_id", "period_start", "period_end"])

    # ── monitoring_alerts ─────────────────────────────────────────────────────

    op.create_table(
        "monitoring_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "alert_type",
            postgresql.ENUM(
                "regulatory_change", "market_shift", "risk_threshold",
                "data_update", "news_alert", "compliance_deadline",
                name="monitoringalerttype", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "severity",
            postgresql.ENUM("info", "warning", "critical",
                            name="monitoringalertseverity", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "domain",
            postgresql.ENUM("market", "climate", "regulatory", "technology", "liquidity",
                            name="monitoringalertdomain", create_type=False),
            nullable=False,
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("data_payload", postgresql.JSONB(), nullable=True),
        sa.Column("affected_entities", postgresql.JSONB(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_actioned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_monitoring_alerts_org_id", "monitoring_alerts", ["org_id"])
    op.create_index("ix_monitoring_alerts_project_id", "monitoring_alerts", ["project_id"])
    op.create_index("ix_monitoring_alerts_portfolio_id", "monitoring_alerts", ["portfolio_id"])
    op.create_index("ix_monitoring_alerts_alert_type", "monitoring_alerts", ["alert_type"])
    op.create_index("ix_monitoring_alerts_severity", "monitoring_alerts", ["severity"])
    op.create_index("ix_monitoring_alerts_is_read", "monitoring_alerts", ["org_id", "is_read"])

    # ── investor_signal_scores ────────────────────────────────────────────────

    op.create_table(
        "investor_signal_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("overall_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("financial_capacity_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("financial_capacity_details", postgresql.JSONB(), nullable=True),
        sa.Column("risk_management_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("risk_management_details", postgresql.JSONB(), nullable=True),
        sa.Column("investment_strategy_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("investment_strategy_details", postgresql.JSONB(), nullable=True),
        sa.Column("team_experience_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("team_experience_details", postgresql.JSONB(), nullable=True),
        sa.Column("esg_commitment_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("esg_commitment_details", postgresql.JSONB(), nullable=True),
        sa.Column("platform_readiness_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("platform_readiness_details", postgresql.JSONB(), nullable=True),
        sa.Column("gaps", postgresql.JSONB(), nullable=True),
        sa.Column("recommendations", postgresql.JSONB(), nullable=True),
        sa.Column("score_factors", postgresql.JSONB(), nullable=True),
        sa.Column("data_sources", postgresql.JSONB(), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_score", sa.Numeric(6, 2), nullable=True),
        sa.Column("score_change", sa.Numeric(6, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_investor_signal_scores_org_id", "investor_signal_scores", ["org_id"])
    op.create_index("ix_investor_signal_scores_org_id_calculated", "investor_signal_scores",
                    ["org_id", "calculated_at"])

    # ── insurance_quotes ──────────────────────────────────────────────────────

    op.create_table(
        "insurance_quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provider_name", sa.String(500), nullable=False),
        sa.Column("coverage_type", sa.String(255), nullable=False),
        sa.Column("coverage_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("quoted_premium", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("terms", postgresql.JSONB(), nullable=True),
        sa.Column(
            "side",
            postgresql.ENUM("ally", "investor", name="insuranceside", create_type=False),
            nullable=False,
            server_default="investor",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_insurance_quotes_org_id", "insurance_quotes", ["org_id"])
    op.create_index("ix_insurance_quotes_project_id", "insurance_quotes", ["project_id"])

    # ── insurance_policies ────────────────────────────────────────────────────

    op.create_table(
        "insurance_policies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quote_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("policy_number", sa.String(255), nullable=False),
        sa.Column("provider_name", sa.String(500), nullable=False),
        sa.Column("coverage_type", sa.String(255), nullable=False),
        sa.Column("coverage_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("premium_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column(
            "premium_frequency",
            postgresql.ENUM("monthly", "quarterly", "annual",
                            name="insurancepremiumfrequency", create_type=False),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("active", "expired", "cancelled", "pending_renewal",
                            name="insurancepolicystatus", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column("risk_score_impact", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("terms", postgresql.JSONB(), nullable=True),
        sa.Column(
            "side",
            postgresql.ENUM("ally", "investor", name="insuranceside", create_type=False),
            nullable=False,
            server_default="investor",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["quote_id"], ["insurance_quotes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_insurance_policies_org_id", "insurance_policies", ["org_id"])
    op.create_index("ix_insurance_policies_quote_id", "insurance_policies", ["quote_id"])
    op.create_index("ix_insurance_policies_project_id", "insurance_policies", ["project_id"])
    op.create_index("ix_insurance_policies_portfolio_id", "insurance_policies", ["portfolio_id"])
    op.create_index("ix_insurance_policies_status", "insurance_policies", ["status"])

    # ── signal_scores: column renames + additions ─────────────────────────────
    # Rename the 4 existing dimension columns (data preserved automatically).
    op.alter_column("signal_scores", "technical_score", new_column_name="project_viability_score")
    op.alter_column("signal_scores", "financial_score", new_column_name="financial_planning_score")
    op.alter_column("signal_scores", "team_score", new_column_name="team_strength_score")
    op.alter_column("signal_scores", "regulatory_score", new_column_name="risk_assessment_score")

    # Add per-dimension details JSONB columns
    for col in [
        "project_viability_details",
        "financial_planning_details",
        "team_strength_details",
        "risk_assessment_details",
        "market_opportunity_details",
        "improvement_guidance",
        "score_factors",
        "data_sources_used",
    ]:
        op.add_column("signal_scores", sa.Column(col, postgresql.JSONB(), nullable=True))

    # Add 6th dimension score
    op.add_column(
        "signal_scores",
        sa.Column("market_opportunity_score", sa.Integer(), nullable=False, server_default="0"),
    )

    # Add is_live flag
    op.add_column(
        "signal_scores",
        sa.Column("is_live", sa.Boolean(), nullable=False, server_default="true"),
    )

    # ── risk_assessments: add 5-domain scores + monitoring fields ─────────────

    for col in [
        "market_risk_details", "market_risk_mitigation",
        "climate_risk_details", "climate_risk_mitigation",
        "regulatory_risk_details", "regulatory_risk_mitigation",
        "technology_risk_details", "technology_risk_mitigation",
        "liquidity_risk_details", "liquidity_risk_mitigation",
        "data_sources",
    ]:
        op.add_column("risk_assessments", sa.Column(col, postgresql.JSONB(), nullable=True))

    for col_name in [
        "overall_risk_score", "market_risk_score", "climate_risk_score",
        "regulatory_risk_score", "technology_risk_score", "liquidity_risk_score",
    ]:
        op.add_column(
            "risk_assessments",
            sa.Column(col_name, sa.Numeric(6, 2), nullable=True),
        )

    op.add_column(
        "risk_assessments",
        sa.Column("monitoring_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.add_column(
        "risk_assessments",
        sa.Column("last_monitoring_check", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "risk_assessments",
        sa.Column("active_alerts_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    conn = op.get_bind()

    # ── Revert risk_assessments additions ─────────────────────────────────────
    for col in [
        "active_alerts_count", "last_monitoring_check", "monitoring_enabled",
        "overall_risk_score", "market_risk_score", "climate_risk_score",
        "regulatory_risk_score", "technology_risk_score", "liquidity_risk_score",
        "market_risk_details", "market_risk_mitigation",
        "climate_risk_details", "climate_risk_mitigation",
        "regulatory_risk_details", "regulatory_risk_mitigation",
        "technology_risk_details", "technology_risk_mitigation",
        "liquidity_risk_details", "liquidity_risk_mitigation",
        "data_sources",
    ]:
        op.drop_column("risk_assessments", col)

    # ── Revert signal_scores additions ────────────────────────────────────────
    op.drop_column("signal_scores", "is_live")
    op.drop_column("signal_scores", "market_opportunity_score")
    for col in [
        "project_viability_details", "financial_planning_details",
        "team_strength_details", "risk_assessment_details",
        "market_opportunity_details", "improvement_guidance",
        "score_factors", "data_sources_used",
    ]:
        op.drop_column("signal_scores", col)

    # Revert column renames
    op.alter_column("signal_scores", "project_viability_score", new_column_name="technical_score")
    op.alter_column("signal_scores", "financial_planning_score", new_column_name="financial_score")
    op.alter_column("signal_scores", "team_strength_score", new_column_name="team_score")
    op.alter_column("signal_scores", "risk_assessment_score", new_column_name="regulatory_score")

    # ── Drop new tables (reverse dependency order) ────────────────────────────
    op.drop_table("insurance_policies")
    op.drop_table("insurance_quotes")
    op.drop_table("investor_signal_scores")
    op.drop_table("monitoring_alerts")
    op.drop_table("capital_efficiency_metrics")
    op.drop_table("equity_scenarios")
    op.drop_table("investor_personas")
    op.drop_table("board_advisor_applications")
    op.drop_table("board_advisor_profiles")

    # ── Drop enums ────────────────────────────────────────────────────────────
    for enum_name in [
        "insuranceside", "insurancepolicystatus", "insurancepremiumfrequency",
        "monitoringalertdomain", "monitoringalertseverity", "monitoringalerttype",
        "antidilutiontype", "equitysecuritytype",
        "investorpersonastrategy", "boardadvisorapplicationstatus",
        "advisorcompensationpreference", "advisoravailabilitystatus",
    ]:
        postgresql.ENUM(name=enum_name).drop(conn, checkfirst=True)
