"""add voice_transcription to aiagenttype enum

Revision ID: m1a2b3c4d5e6
Revises: l1a2b3c4d5e6
Create Date: 2026-03-14 12:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "m1a2b3c4d5e6"
down_revision = "l1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE is allowed inside transactions on PostgreSQL 12+.
    # IF NOT EXISTS makes the migration idempotent.
    op.execute(sa.text("ALTER TYPE aiagenttype ADD VALUE IF NOT EXISTS 'voice_transcription'"))


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; downgrade is a no-op.
    pass
