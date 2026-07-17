from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from insight_engine.api.deps import get_current_user, get_user_portfolio
from insight_engine.api.schemas import (
    PortfolioAsset,
    PositionResponse,
    PositionUpdateRequest,
)
from insight_engine.database import get_session
from insight_engine.domain.models import Position, User

router = APIRouter(prefix="/portfolio/positions", tags=["positions"])

MAX_TICKERS = 20


def _to_response(position: Position) -> PositionResponse:
    return PositionResponse(
        id=position.id,
        ticker=position.ticker,
        quantity=position.quantity,
        purchase_price=position.purchase_price,
        purchase_date=position.purchase_date,
        updated_at=position.updated_at,
    )


@router.get("", response_model=list[PositionResponse])
async def list_positions(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List the user's position lots. Does not trigger analysis."""
    portfolio = await get_user_portfolio(user, session)
    if portfolio is None:
        return []
    result = await session.execute(
        select(Position)
        .where(Position.portfolio_id == portfolio.id)
        .order_by(Position.ticker, Position.id)
    )
    return [_to_response(p) for p in result.scalars().all()]


@router.post("", response_model=PositionResponse, status_code=201)
async def add_position(
    request: PortfolioAsset,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Add a purchase lot. The same ticker can be added multiple times at
    different prices; analysis aggregates lots per ticker.

    Does not trigger analysis; run POST /portfolio/analyze for that.
    """
    portfolio = await get_user_portfolio(user, session, create=True)
    ticker = request.ticker.upper()

    result = await session.execute(
        select(Position.ticker)
        .where(Position.portfolio_id == portfolio.id)
        .distinct()
    )
    tickers = set(result.scalars().all())
    if ticker not in tickers and len(tickers) >= MAX_TICKERS:
        raise HTTPException(
            status_code=422,
            detail=f"Portfolio is limited to {MAX_TICKERS} distinct tickers",
        )

    position = Position(
        portfolio_id=portfolio.id,
        ticker=ticker,
        quantity=request.quantity,
        purchase_price=request.purchase_price,
        purchase_date=request.purchase_date,
    )
    session.add(position)
    await session.commit()
    return _to_response(position)


@router.patch("/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: int,
    request: PositionUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update quantity or purchase details of a lot."""
    position = await _get_position_or_404(position_id, user, session)

    if request.quantity is not None:
        position.quantity = request.quantity
    if request.purchase_price is not None:
        position.purchase_price = request.purchase_price
    if request.purchase_date is not None:
        position.purchase_date = request.purchase_date

    await session.commit()
    # updated_at is set server-side on UPDATE; reload it before serializing
    await session.refresh(position)
    return _to_response(position)


@router.delete("/{position_id}", status_code=204)
async def delete_position(
    position_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Remove a lot. Insight history for the ticker is kept."""
    position = await _get_position_or_404(position_id, user, session)
    await session.delete(position)
    await session.commit()


async def _get_position_or_404(
    position_id: int, user: User, session: AsyncSession
) -> Position:
    portfolio = await get_user_portfolio(user, session)
    if portfolio is not None:
        result = await session.execute(
            select(Position).where(
                Position.portfolio_id == portfolio.id,
                Position.id == position_id,
            )
        )
        position = result.scalar_one_or_none()
        if position is not None:
            return position
    raise HTTPException(status_code=404, detail=f"Position {position_id} not found")
