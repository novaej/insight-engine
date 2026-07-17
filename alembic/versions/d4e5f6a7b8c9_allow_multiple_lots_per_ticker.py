"""allow multiple lots per ticker in positions

Drops the (portfolio_id, ticker) unique constraint so each purchase can be its
own row (a lot), and replaces it with a plain index for lookups.

Downgrade recreates the unique constraint — it will fail if any ticker has
multiple lots; merge them first.

Revision ID: d4e5f6a7b8c9
Revises: b7d9e0f1a2c3
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'b7d9e0f1a2c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('positions_portfolio_id_ticker_key', 'positions', type_='unique')
    op.create_index('ix_positions_portfolio_ticker', 'positions', ['portfolio_id', 'ticker'])


def downgrade() -> None:
    op.drop_index('ix_positions_portfolio_ticker', table_name='positions')
    op.create_unique_constraint(
        'positions_portfolio_id_ticker_key', 'positions', ['portfolio_id', 'ticker']
    )
