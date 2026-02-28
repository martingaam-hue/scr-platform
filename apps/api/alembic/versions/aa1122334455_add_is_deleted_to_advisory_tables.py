"""add_is_deleted_to_advisory_tables

Revision ID: aa1122334455
Revises: ff0011223344
Create Date: 2026-02-28 21:00:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "aa1122334455"
down_revision = "ff0011223344"
branch_labels = None
depends_on = None

TABLES = [
    "board_advisor_profiles",
    "board_advisor_applications",
    "investor_personas",
    "equity_scenarios",
    "capital_efficiency_metrics",
    "monitoring_alerts",
    "investor_signal_scores",
    "insurance_quotes",
    "insurance_policies",
]


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                "is_deleted",
                sa.Boolean(),
                nullable=False,
                server_default="false",
            ),
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "is_deleted")
