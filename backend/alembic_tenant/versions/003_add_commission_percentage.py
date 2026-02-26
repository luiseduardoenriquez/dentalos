"""add commission_percentage to users

Revision ID: 003_add_commission_percentage
Revises: 002_messaging_referrals
Create Date: 2026-02-26 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003_add_commission_percentage'
down_revision: Union[str, None] = '002_messaging_referrals'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('commission_percentage', sa.Numeric(5, 2), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'commission_percentage')
