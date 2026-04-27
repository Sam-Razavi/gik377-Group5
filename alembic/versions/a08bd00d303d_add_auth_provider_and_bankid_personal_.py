"""add auth provider and bankid personal number to user

Revision ID: a08bd00d303d
Revises: 9529eda66349
Create Date: 2026-04-18 16:35:27.848895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a08bd00d303d'
down_revision: Union[str, Sequence[str], None] = '9529eda66349'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('auth_provider', sa.String(), nullable=False, server_default='local')
    )
    op.add_column(
        'users',
        sa.Column('bankid_personal_number', sa.String(), nullable=True)
    )
    op.create_unique_constraint(
        'uq_users_bankid_personal_number',
        'users',
        ['bankid_personal_number']
    )

    op.alter_column('users', 'auth_provider', server_default=None)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_users_bankid_personal_number', 'users', type_='unique')
    op.drop_column('users', 'bankid_personal_number')
    op.drop_column('users', 'auth_provider')
    # ### end Alembic commands ###
