"""add two factor fields to users

Revision ID: fdfde8176428
Revises: c6d6e5a4f0ee
Create Date: 2026-04-27 15:28:04.138423

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fdfde8176428"
down_revision: Union[str, Sequence[str], None] = "c6d6e5a4f0ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add two-factor authentication fields to users table."""
    op.add_column(
        "users",
        sa.Column(
            "two_factor_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "two_factor_secret",
            sa.String(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Remove two-factor authentication fields from users table."""
    op.drop_column("users", "two_factor_secret")
    op.drop_column("users", "two_factor_enabled")