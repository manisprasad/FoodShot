"""create tables

Revision ID: 90af9772b2b8
Revises: ed3af4901824
Create Date: 2026-07-08 16:23:40.449901

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "90af9772b2b8"
down_revision: Union[str, Sequence[str], None] = "ed3af4901824"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("icr", sa.Float(), nullable=False),
        sa.Column("isf", sa.Float(), nullable=False),
        sa.Column("target_bg", sa.Float(), nullable=False),
        sa.Column("insulin_type", sa.String(length=50), nullable=True),
        sa.Column("language", sa.String(length=5), server_default="en", nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "meal_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "user_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("dish_name", sa.String(length=255), nullable=True),
        sa.Column("portion_g", sa.Float(), nullable=True),
        sa.Column("carbs_g", sa.Float(), nullable=True),
        sa.Column("kcal", sa.Float(), nullable=True),
        sa.Column("protein_g", sa.Float(), nullable=True),
        sa.Column("fat_g", sa.Float(), nullable=True),
        sa.Column("bolus_dose", sa.Float(), nullable=True),
        sa.Column("current_bg", sa.Float(), nullable=True),
        sa.Column("photo_file_id", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("meal_logs")
    op.drop_table("users")
