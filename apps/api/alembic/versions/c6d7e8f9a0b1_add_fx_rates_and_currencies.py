"""add_fx_rates_and_currencies

Revision ID: c6d7e8f9a0b1
Revises: c3d4e5f6a7b8
Create Date: 2026-02-28 00:05:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "c6d7e8f9a0b1"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fx_rates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("base_currency", sa.String(3), nullable=False),
        sa.Column("quote_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Float(), nullable=False),
        sa.Column("rate_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(20), server_default="ecb", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("base_currency", "quote_currency", "rate_date", name="uq_fx_pair_date"),
    )
    op.create_index("ix_fx_rates_rate_date", "fx_rates", ["rate_date"])
    op.create_index("ix_fx_pair_date_lookup", "fx_rates", ["base_currency", "quote_currency", "rate_date"])

    # Add currency columns to existing tables
    op.add_column("projects", sa.Column("project_currency", sa.String(3), server_default="EUR", nullable=True))


def downgrade() -> None:
    op.drop_column("projects", "project_currency")
    op.drop_index("ix_fx_pair_date_lookup", table_name="fx_rates")
    op.drop_index("ix_fx_rates_rate_date", table_name="fx_rates")
    op.drop_table("fx_rates")
