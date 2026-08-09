"""add_freemium_and_subscription_fields

Revision ID: e7f890123456
Revises: ddd6b9f4501c
Create Date: 2026-07-28 18:38:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f890123456"
down_revision: str | Sequence[str] | None = "ddd6b9f4501c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column("is_premium", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("users", sa.Column("premium_until", sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "premium_until")
    op.drop_column("users", "is_premium")
