"""add VOICE_TRANSCRIPTION (uppercase) to aiagenttype enum

The previous migration (m1a2b3c4d5e6) added the lowercase value
'voice_transcription' but all other aiagenttype enum values in the
database are uppercase. SQLAlchemy 2.0 binds str-enum values by name
(uppercase), so inserting AIAgentType.VOICE_TRANSCRIPTION would fail
when only the lowercase variant exists.

This migration adds the uppercase value so the column binding is consistent
with the rest of the enum.

Revision ID: o1a2b3c4d5e6
Revises: n1a2b3c4d5e6
Create Date: 2026-03-14 12:30:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "o1a2b3c4d5e6"
down_revision = "n1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("ALTER TYPE aiagenttype ADD VALUE IF NOT EXISTS 'VOICE_TRANSCRIPTION'"))


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; downgrade is a no-op.
    pass
