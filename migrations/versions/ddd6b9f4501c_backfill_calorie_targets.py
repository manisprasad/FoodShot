"""backfill_calorie_targets

Revision ID: ddd6b9f4501c
Revises: 2e4ae1dbd023
Create Date: 2026-07-13 23:30:55.170386

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ddd6b9f4501c'
down_revision: Union[str, Sequence[str], None] = '2e4ae1dbd023'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "UPDATE users SET daily_calorie_target = 2000 WHERE daily_calorie_target IS NULL"
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass

