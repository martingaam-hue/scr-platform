"""merge_c_series_c01_to_c05

Revision ID: c0merge0c01c05
Revises: c1a2b3c4d5e6, c2a2b3c4d5e6, c3a2b3c4d5e6, c4a2b3c4d5e6, c5a2b3c4d5e6
Create Date: 2026-03-01 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c0merge0c01c05"
down_revision = (
    "c1a2b3c4d5e6",
    "c2a2b3c4d5e6",
    "c3a2b3c4d5e6",
    "c4a2b3c4d5e6",
    "c5a2b3c4d5e6",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
