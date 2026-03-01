"""add_cashflow_pacing

Revision ID: c6a2b3c4d5e6
Revises: c0merge0c01c05
Create Date: 2026-03-01 13:00:00.000000

Creates cashflow_assumptions and cashflow_projections tables
for the C06 J-curve cashflow pacing feature.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c6a2b3c4d5e6"
down_revision: Union[str, tuple[str, ...]] = "c0merge0c01c05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # cashflow_assumptions
    op.create_table(
        "cashflow_assumptions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("portfolio_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("committed_capital", sa.Numeric(18, 4), nullable=False),
        sa.Column("investment_period_years", sa.Integer(), server_default="5", nullable=False),
        sa.Column("fund_life_years", sa.Integer(), server_default="10", nullable=False),
        sa.Column("optimistic_modifier", sa.Numeric(6, 4), server_default="1.2000", nullable=False),
        sa.Column("pessimistic_modifier", sa.Numeric(6, 4), server_default="0.8000", nullable=False),
        sa.Column(
            "deployment_schedule",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "distribution_schedule",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "portfolio_id", "is_active", name="uq_one_active_pacing_per_portfolio"
        ),
    )
    op.create_index("ix_cashflow_assumptions_portfolio_id", "cashflow_assumptions", ["portfolio_id"])

    # cashflow_projections
    op.create_table(
        "cashflow_projections",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("assumption_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("scenario", sa.String(length=20), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        # Projected
        sa.Column("projected_contributions", sa.Numeric(18, 4), nullable=True),
        sa.Column("projected_distributions", sa.Numeric(18, 4), nullable=True),
        sa.Column("projected_nav", sa.Numeric(18, 4), nullable=True),
        sa.Column("projected_net_cashflow", sa.Numeric(18, 4), nullable=True),
        # Actual
        sa.Column("actual_contributions", sa.Numeric(18, 4), nullable=True),
        sa.Column("actual_distributions", sa.Numeric(18, 4), nullable=True),
        sa.Column("actual_nav", sa.Numeric(18, 4), nullable=True),
        sa.Column("actual_net_cashflow", sa.Numeric(18, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["assumption_id"], ["cashflow_assumptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assumption_id", "scenario", "year", name="uq_cashflow_projection_row"
        ),
    )
    op.create_index(
        "ix_cashflow_projections_assumption_id", "cashflow_projections", ["assumption_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_cashflow_projections_assumption_id", table_name="cashflow_projections")
    op.drop_table("cashflow_projections")
    op.drop_index("ix_cashflow_assumptions_portfolio_id", table_name="cashflow_assumptions")
    op.drop_table("cashflow_assumptions")
