"""add_comparable_transactions

Revision ID: f3a4b5c6d7e8
Revises: a7b8c9d0e1f2
Create Date: 2026-02-28 00:02:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f3a4b5c6d7e8"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "comparable_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deal_name", sa.String(200), nullable=False),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("geography", sa.String(100), nullable=True),
        sa.Column("country_code", sa.String(3), nullable=True),
        sa.Column("close_date", sa.Date(), nullable=True),
        sa.Column("close_year", sa.Integer(), nullable=True),
        sa.Column("deal_size_eur", sa.Float(), nullable=True),
        sa.Column("capacity_mw", sa.Float(), nullable=True),
        sa.Column("ev_per_mw", sa.Float(), nullable=True),
        sa.Column("equity_value_eur", sa.Float(), nullable=True),
        sa.Column("equity_irr", sa.Float(), nullable=True),
        sa.Column("project_irr", sa.Float(), nullable=True),
        sa.Column("ebitda_multiple", sa.Float(), nullable=True),
        sa.Column("stage_at_close", sa.String(50), nullable=True),
        sa.Column("offtake_type", sa.String(50), nullable=True),
        sa.Column("offtake_counterparty_rating", sa.String(10), nullable=True),
        sa.Column("buyer_type", sa.String(50), nullable=True),
        sa.Column("seller_type", sa.String(50), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("data_quality", sa.String(20), server_default="estimated", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.JSONB(), nullable=True),
        sa.Column("added_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comparable_transactions_org_id", "comparable_transactions", ["org_id"])
    op.create_index("ix_comparable_transactions_asset_type", "comparable_transactions", ["asset_type"])
    op.create_index("ix_comparable_transactions_close_year", "comparable_transactions", ["close_year"])


def downgrade() -> None:
    op.drop_index("ix_comparable_transactions_close_year", table_name="comparable_transactions")
    op.drop_index("ix_comparable_transactions_asset_type", table_name="comparable_transactions")
    op.drop_index("ix_comparable_transactions_org_id", table_name="comparable_transactions")
    op.drop_table("comparable_transactions")
