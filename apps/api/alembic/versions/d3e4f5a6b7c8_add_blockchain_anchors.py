"""add_blockchain_anchors

Revision ID: d3e4f5a6b7c8
Revises: e2f3a4b5c6d7
Create Date: 2026-02-28 01:05:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d3e4f5a6b7c8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blockchain_anchors",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_hash", sa.String(66), nullable=False),
        sa.Column("merkle_root", sa.String(66), nullable=True),
        sa.Column("merkle_proof", sa.String(4000), nullable=True),
        sa.Column("chain", sa.String(20), server_default="polygon", nullable=False),
        sa.Column("tx_hash", sa.String(66), nullable=True),
        sa.Column("block_number", sa.Integer, nullable=True),
        sa.Column("anchored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("is_deleted", sa.Boolean, server_default="false", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_anchor_entity", "blockchain_anchors", ["entity_type", "entity_id"])
    op.create_index("ix_anchor_org_status", "blockchain_anchors", ["org_id", "status"])
    op.create_index("ix_anchor_tx_hash", "blockchain_anchors", ["tx_hash"])
    op.create_index("ix_anchor_batch_id", "blockchain_anchors", ["batch_id"])
    op.create_index("ix_anchor_event_type", "blockchain_anchors", ["event_type"])


def downgrade() -> None:
    op.drop_table("blockchain_anchors")
