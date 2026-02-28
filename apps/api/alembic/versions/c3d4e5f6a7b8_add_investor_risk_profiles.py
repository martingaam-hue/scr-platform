"""Add investor_risk_profiles table.

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-02-28 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investor_risk_profiles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("experience_level", sa.String(50), nullable=False),
        sa.Column("investment_horizon_years", sa.Integer(), nullable=False),
        sa.Column("loss_tolerance_percentage", sa.Integer(), nullable=False),
        sa.Column("liquidity_needs", sa.String(20), nullable=False),
        sa.Column("concentration_max_percentage", sa.Integer(), nullable=False),
        sa.Column("max_drawdown_tolerance", sa.Integer(), nullable=False),
        sa.Column("sophistication_score", sa.Float(), nullable=False),
        sa.Column("risk_appetite_score", sa.Float(), nullable=False),
        sa.Column("risk_category", sa.String(20), nullable=False),
        sa.Column(
            "recommended_allocation",
            postgresql.JSONB(),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_investor_risk_profiles_user_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_investor_risk_profiles_user_id", "investor_risk_profiles", ["user_id"])
    op.create_index("ix_investor_risk_profiles_org_id", "investor_risk_profiles", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_investor_risk_profiles_org_id", table_name="investor_risk_profiles")
    op.drop_index("ix_investor_risk_profiles_user_id", table_name="investor_risk_profiles")
    op.drop_table("investor_risk_profiles")
