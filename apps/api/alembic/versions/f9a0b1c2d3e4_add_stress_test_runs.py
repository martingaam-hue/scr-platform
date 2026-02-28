"""add_stress_test_runs

Revision ID: f9a0b1c2d3e4
Revises: f3a4b5c6d7e8
Create Date: 2026-02-28 01:01:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f9a0b1c2d3e4"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stress_test_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario_key", sa.String(100), nullable=False),
        sa.Column("scenario_name", sa.String(255), nullable=False),
        sa.Column("parameters", postgresql.JSONB, server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("simulations_count", sa.Integer, server_default="10000", nullable=False),
        sa.Column("base_nav", sa.Float, nullable=False),
        sa.Column("mean_nav", sa.Float, nullable=False),
        sa.Column("median_nav", sa.Float, nullable=False),
        sa.Column("p5_nav", sa.Float, nullable=False),
        sa.Column("p95_nav", sa.Float, nullable=False),
        sa.Column("var_95", sa.Float, nullable=False),
        sa.Column("max_loss_pct", sa.Float, nullable=False),
        sa.Column("probability_of_loss", sa.Float, nullable=False),
        sa.Column("histogram", postgresql.JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("histogram_edges", postgresql.JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("project_sensitivities", postgresql.JSONB, server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_stress_portfolio_created", "stress_test_runs", ["portfolio_id", "created_at"])
    op.create_index("ix_stress_test_runs_org_id", "stress_test_runs", ["org_id"])


def downgrade() -> None:
    op.drop_table("stress_test_runs")
