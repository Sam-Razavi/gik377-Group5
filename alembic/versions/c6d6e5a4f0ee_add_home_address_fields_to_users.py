"""add home address fields to users

Revision ID: c6d6e5a4f0ee
Revises: a08bd00d303d
Create Date: 2026-04-27 14:41:44.688842

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c6d6e5a4f0ee"
down_revision: Union[str, Sequence[str], None] = "a08bd00d303d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add optional home address fields to users table."""
    op.add_column("users", sa.Column("home_address", sa.String(), nullable=True))
    op.add_column("users", sa.Column("home_lat", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("home_lon", sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove optional home address fields from users table."""
    op.drop_column("users", "home_lon")
    op.drop_column("users", "home_lat")
    op.drop_column("users", "home_address")