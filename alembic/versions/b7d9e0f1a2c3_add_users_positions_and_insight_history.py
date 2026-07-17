"""add users and positions tables, keep insight history

Backfills existing data: creates a default user (default@localhost), links the
existing portfolio to it, and converts the portfolios.assets JSON blob into
positions rows before dropping the column.

Downgrade reassembles the JSON blob from positions (purchase_price and
purchase_date are lost — acceptable, they had no pre-upgrade equivalent).

Revision ID: b7d9e0f1a2c3
Revises: ce12def4114e
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7d9e0f1a2c3'
down_revision: Union[str, None] = 'ce12def4114e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_USER_EMAIL = "default@localhost"


def upgrade() -> None:
    # 1. Users table + default user
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=True),
        sa.Column('api_token_hash', sa.String(length=64), nullable=True, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    bind = op.get_bind()
    result = bind.execute(
        sa.text("INSERT INTO users (email, name) VALUES (:email, :name) RETURNING id"),
        {"email": DEFAULT_USER_EMAIL, "name": "Default User"},
    )
    default_user_id = result.scalar_one()

    # 2. Link portfolios to the default user
    op.add_column('portfolios', sa.Column('user_id', sa.Integer(), nullable=True))
    bind.execute(
        sa.text("UPDATE portfolios SET user_id = :uid"), {"uid": default_user_id}
    )
    op.alter_column('portfolios', 'user_id', nullable=False)
    op.create_unique_constraint('uq_portfolios_user_id', 'portfolios', ['user_id'])
    op.create_foreign_key(
        'fk_portfolios_user_id', 'portfolios', 'users', ['user_id'], ['id'],
        ondelete='CASCADE',
    )

    # 3. Positions table, backfilled from the assets JSON blob
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column(
            'portfolio_id', sa.Integer(),
            sa.ForeignKey('portfolios.id', ondelete='CASCADE'),
            nullable=False, index=True,
        ),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('purchase_price', sa.Float(), nullable=True),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('portfolio_id', 'ticker'),
    )
    rows = bind.execute(sa.text("SELECT id, assets FROM portfolios")).fetchall()
    for portfolio_id, assets in rows:
        if isinstance(assets, str):
            import json
            assets = json.loads(assets)
        for asset in assets or []:
            if not asset.get("ticker"):
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO positions (portfolio_id, ticker, quantity) "
                    "VALUES (:pid, :ticker, :quantity)"
                ),
                {
                    "pid": portfolio_id,
                    "ticker": asset["ticker"].upper(),
                    "quantity": asset.get("quantity", 0) or 0,
                },
            )

    # 4. Drop the JSON blob, now redundant
    op.drop_column('portfolios', 'assets')

    # 5. Index for latest-per-ticker and history queries
    op.create_index(
        'ix_insights_portfolio_ticker_created',
        'insights',
        ['portfolio_id', 'ticker', 'created_at'],
    )


def downgrade() -> None:
    op.drop_index('ix_insights_portfolio_ticker_created', table_name='insights')

    op.add_column(
        'portfolios',
        sa.Column('assets', sa.dialects.postgresql.JSON(), nullable=True),
    )
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT portfolio_id, ticker, quantity FROM positions ORDER BY id")
    ).fetchall()
    assets_by_portfolio: dict[int, list[dict]] = {}
    for portfolio_id, ticker, quantity in rows:
        assets_by_portfolio.setdefault(portfolio_id, []).append(
            {"ticker": ticker, "quantity": quantity}
        )
    import json
    for portfolio_id, assets in assets_by_portfolio.items():
        bind.execute(
            sa.text("UPDATE portfolios SET assets = :assets WHERE id = :pid"),
            {"assets": json.dumps(assets), "pid": portfolio_id},
        )
    bind.execute(sa.text("UPDATE portfolios SET assets = '[]' WHERE assets IS NULL"))
    op.alter_column('portfolios', 'assets', nullable=False)

    op.drop_table('positions')

    op.drop_constraint('fk_portfolios_user_id', 'portfolios', type_='foreignkey')
    op.drop_constraint('uq_portfolios_user_id', 'portfolios', type_='unique')
    op.drop_column('portfolios', 'user_id')
    op.drop_table('users')
