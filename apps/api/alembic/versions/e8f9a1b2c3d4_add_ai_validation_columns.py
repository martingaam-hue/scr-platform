"""Add validation columns to ai_task_logs

Revision ID: e8f9a1b2c3d4
Revises: 7c4e82b31d09
Create Date: 2026-02-28 12:00:00.000000

Adds confidence tracking columns so every AI call records its validation metadata.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "e8f9a1b2c3d4"
down_revision: Union[str, None] = "7c4e82b31d09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ai_task_logs", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("ai_task_logs", sa.Column("confidence_level", sa.String(20), nullable=True))
    op.add_column("ai_task_logs", sa.Column("validation_repairs", JSONB(), nullable=True))
    op.add_column("ai_task_logs", sa.Column("validation_warnings", JSONB(), nullable=True))
    op.create_index("ix_ai_task_logs_confidence", "ai_task_logs", ["confidence"])
    op.create_index("ix_ai_task_logs_confidence_level", "ai_task_logs", ["confidence_level"])


def downgrade() -> None:
    op.drop_index("ix_ai_task_logs_confidence_level", table_name="ai_task_logs")
    op.drop_index("ix_ai_task_logs_confidence", table_name="ai_task_logs")
    op.drop_column("ai_task_logs", "validation_warnings")
    op.drop_column("ai_task_logs", "validation_repairs")
    op.drop_column("ai_task_logs", "confidence_level")
    op.drop_column("ai_task_logs", "confidence")
