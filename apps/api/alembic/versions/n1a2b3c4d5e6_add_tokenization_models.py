"""add tokenization models

Revision ID: n1a2b3c4d5e6
Revises: m1a2b3c4d5e6
Create Date: 2026-03-14 14:00:00.000000

Replaces the old AITaskLog-based approach with three dedicated tables:
  tokenization_records  — one per (org, project, token_symbol)
  token_holdings        — mutable cap-table entries
  token_transfers       — append-only audit log (mint / transfer / burn)
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "n1a2b3c4d5e6"
down_revision = "m1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tokenization_records ──────────────────────────────────────────────────
    op.create_table(
        "tokenization_records",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_name", sa.String(255), nullable=False),
        sa.Column("token_symbol", sa.String(10), nullable=False),
        sa.Column("total_supply", sa.Numeric(19, 4), nullable=False),
        sa.Column("token_price_usd", sa.Numeric(19, 4), nullable=False),
        sa.Column("blockchain", sa.String(100), server_default="Ethereum", nullable=False),
        sa.Column("token_type", sa.String(50), server_default="security", nullable=False),
        sa.Column("regulatory_framework", sa.String(100), server_default="Reg D", nullable=False),
        sa.Column(
            "minimum_investment_usd", sa.Numeric(19, 4), server_default="1000", nullable=False
        ),
        sa.Column("lock_up_period_days", sa.Integer(), server_default="365", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column(
            "status_changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "org_id", "project_id", "token_symbol", name="uq_tokenization_org_project_symbol"
        ),
    )
    op.create_index("ix_tokenization_records_org_id", "tokenization_records", ["org_id"])
    op.create_index("ix_tokenization_records_project_id", "tokenization_records", ["project_id"])

    # ── token_holdings ────────────────────────────────────────────────────────
    op.create_table(
        "token_holdings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tokenization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("holder_name", sa.String(255), nullable=False),
        sa.Column("holder_type", sa.String(50), nullable=False),
        sa.Column("tokens", sa.Numeric(19, 4), nullable=False),
        sa.Column("percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["tokenization_id"], ["tokenization_records.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_token_holdings_tokenization_id", "token_holdings", ["tokenization_id"])

    # ── token_transfers ───────────────────────────────────────────────────────
    op.create_table(
        "token_transfers",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("tokenization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("from_holding_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("to_holding_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("transfer_type", sa.String(20), nullable=False),
        sa.Column(
            "executed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("executed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tx_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["tokenization_id"], ["tokenization_records.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["from_holding_id"], ["token_holdings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["to_holding_id"], ["token_holdings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_token_transfers_tokenization_id", "token_transfers", ["tokenization_id"])
    op.create_index("ix_token_transfers_executed_at", "token_transfers", ["executed_at"])


def downgrade() -> None:
    op.drop_table("token_transfers")
    op.drop_table("token_holdings")
    op.drop_table("tokenization_records")
