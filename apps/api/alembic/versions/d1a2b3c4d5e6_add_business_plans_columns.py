"""add_business_plans_columns

Revision ID: d1a2b3c4d5e6
Revises: c9merge0c06c08
Create Date: 2026-03-01 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "d1a2b3c4d5e6"
down_revision = "c9merge0c06c08"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to existing business_plans table
    op.add_column(
        "business_plans",
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "business_plans",
        sa.Column("use_of_funds", sa.Text(), nullable=True),
    )
    op.add_column(
        "business_plans",
        sa.Column("team_section", sa.Text(), nullable=True),
    )
    op.add_column(
        "business_plans",
        sa.Column("risk_section", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("business_plans", "risk_section")
    op.drop_column("business_plans", "team_section")
    op.drop_column("business_plans", "use_of_funds")
    op.drop_column("business_plans", "created_by")
