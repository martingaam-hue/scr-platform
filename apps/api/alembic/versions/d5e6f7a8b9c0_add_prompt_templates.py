"""Add prompt_templates table and prompt tracking to ai_task_logs

Revision ID: d5e6f7a8b9c0
Revises: e8f9a1b2c3d4
Create Date: 2026-02-28 13:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "e8f9a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── prompt_templates table ─────────────────────────────────────────────────
    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("task_type", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("user_prompt_template", sa.Text(), nullable=False),
        sa.Column("variables_schema", JSONB(), nullable=False, server_default="{}"),
        sa.Column("output_format_instruction", sa.Text(), nullable=True),
        sa.Column("model_override", sa.String(100), nullable=True),
        sa.Column("temperature_override", sa.Float(), nullable=True),
        sa.Column("max_tokens_override", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("traffic_percentage", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("total_uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_confidence", sa.Float(), nullable=True),
        sa.Column("positive_feedback_rate", sa.Float(), nullable=True),
        sa.Column("avg_latency_ms", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_type", "version", name="uq_prompt_task_version"),
    )
    op.create_index("ix_prompt_templates_task_type", "prompt_templates", ["task_type"])
    op.create_index("ix_prompt_templates_active", "prompt_templates", ["is_active"])

    # ── ai_task_logs: add prompt tracking columns ──────────────────────────────
    op.add_column("ai_task_logs", sa.Column("prompt_template_id", sa.UUID(), nullable=True))
    op.add_column("ai_task_logs", sa.Column("prompt_version", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_ai_task_logs_prompt_template",
        "ai_task_logs", "prompt_templates",
        ["prompt_template_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_ai_task_logs_prompt_template", "ai_task_logs", type_="foreignkey")
    op.drop_column("ai_task_logs", "prompt_version")
    op.drop_column("ai_task_logs", "prompt_template_id")
    op.drop_index("ix_prompt_templates_active", table_name="prompt_templates")
    op.drop_index("ix_prompt_templates_task_type", table_name="prompt_templates")
    op.drop_table("prompt_templates")
