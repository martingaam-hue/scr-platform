"""merge_all_heads

Revision ID: 1793197fd8ed
Revises: a9b8c7d6e5f4, b9c8d7e6f5a4, h2a2b3c4d5e6
Create Date: 2026-03-01 14:59:57.528426

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1793197fd8ed'
down_revision: Union[str, None] = ('a9b8c7d6e5f4', 'b9c8d7e6f5a4', 'h2a2b3c4d5e6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
