"""merge_index_and_ai_cost_branches

Revision ID: 8d141fa29a9e
Revises: 4b570868cd8e, i1a2b3c4d5e6
Create Date: 2026-03-01 15:35:41.141883

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "8d141fa29a9e"
down_revision: str | None = ("4b570868cd8e", "i1a2b3c4d5e6")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
