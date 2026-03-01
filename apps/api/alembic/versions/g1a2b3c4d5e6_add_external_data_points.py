"""Add external_data_points table.

Revision ID: g1a2b3c4d5e6
Revises: e3a2b3c4d5e6
Create Date: 2026-03-01 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "g1a2b3c4d5e6"
down_revision = "e3a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_data_points",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("series_id", sa.String(100), nullable=False),
        sa.Column("series_name", sa.String(255), nullable=False),
        sa.Column("data_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit", sa.String(50), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "source", "series_id", "data_date",
            name="uq_external_data_point",
        ),
    )
    op.create_index(
        "ix_external_data_source_series",
        "external_data_points",
        ["source", "series_id"],
    )
    op.create_index(
        "ix_external_data_date",
        "external_data_points",
        ["data_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_external_data_date", table_name="external_data_points")
    op.drop_index("ix_external_data_source_series", table_name="external_data_points")
    op.drop_table("external_data_points")
