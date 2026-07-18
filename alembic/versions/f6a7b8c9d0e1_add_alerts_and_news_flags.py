"""add users.alerts_enabled and insights.news_flags

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'alerts_enabled', sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.add_column('insights', sa.Column('news_flags', JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('insights', 'news_flags')
    op.drop_column('users', 'alerts_enabled')
