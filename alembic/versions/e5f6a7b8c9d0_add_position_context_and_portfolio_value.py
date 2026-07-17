"""add position context to insights and value/concentration to portfolios

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('insights', sa.Column('position_context', JSON(), nullable=True))
    op.add_column('portfolios', sa.Column('total_value', sa.Float(), nullable=True))
    op.add_column('portfolios', sa.Column('concentration', JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('portfolios', 'concentration')
    op.drop_column('portfolios', 'total_value')
    op.drop_column('insights', 'position_context')
