"""add_backtesting

Revision ID: e1a2b3c4d5e6
Revises: d1a2b3c4d5e6
Create Date: 2026-03-01 13:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e1a2b3c4d5e6"
down_revision = "d1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── deal_outcomes ──────────────────────────────────────────────────────
    op.create_table(
        "deal_outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="SET NULL"), nullable=True),
        # deal_flow_stages table does not exist — plain UUID column
        sa.Column("deal_flow_stage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("outcome_type", sa.VARCHAR(50), nullable=False),
        sa.Column("actual_irr", sa.NUMERIC(10, 4), nullable=True),
        sa.Column("actual_moic", sa.NUMERIC(10, 4), nullable=True),
        sa.Column("actual_revenue_eur", sa.NUMERIC(19, 4), nullable=True),
        sa.Column("signal_score_at_evaluation", sa.NUMERIC(5, 2), nullable=True),
        sa.Column("signal_score_at_decision", sa.NUMERIC(5, 2), nullable=True),
        sa.Column("signal_dimensions_at_decision", postgresql.JSONB(), nullable=True),
        sa.Column("decision_date", sa.DATE(), nullable=True),
        sa.Column("outcome_date", sa.DATE(), nullable=True),
        sa.Column("notes", sa.TEXT(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_deal_outcomes_org_id", "deal_outcomes", ["org_id"])
    op.create_index("ix_deal_outcomes_project_id", "deal_outcomes", ["project_id"])

    # ── backtest_runs ──────────────────────────────────────────────────────
    op.create_table(
        "backtest_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("orgs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("methodology", sa.VARCHAR(50), nullable=False, server_default="threshold"),
        sa.Column("date_from", sa.DATE(), nullable=True),
        sa.Column("date_to", sa.DATE(), nullable=True),
        sa.Column("min_score_threshold", sa.NUMERIC(5, 2), nullable=True),
        sa.Column("accuracy", sa.NUMERIC(5, 4), nullable=True),
        sa.Column("precision", sa.NUMERIC(5, 4), nullable=True),
        sa.Column("recall", sa.NUMERIC(5, 4), nullable=True),
        sa.Column("auc_roc", sa.NUMERIC(5, 4), nullable=True),
        sa.Column("f1_score", sa.NUMERIC(5, 4), nullable=True),
        sa.Column("sample_size", sa.INTEGER(), nullable=True),
        sa.Column("results", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_backtest_runs_org_id", "backtest_runs", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_backtest_runs_org_id", table_name="backtest_runs")
    op.drop_table("backtest_runs")
    op.drop_index("ix_deal_outcomes_project_id", table_name="deal_outcomes")
    op.drop_index("ix_deal_outcomes_org_id", table_name="deal_outcomes")
    op.drop_table("deal_outcomes")
