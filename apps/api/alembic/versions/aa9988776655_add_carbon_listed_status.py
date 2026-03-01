"""add carbon listed status

Revision ID: aa9988776655
Revises: ff0011223344
Create Date: 2026-03-01 00:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "aa9988776655"
down_revision = "ff0011223344"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE carbonverificationstatus ADD VALUE IF NOT EXISTS 'listed'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values; downgrade is a no-op
    pass
