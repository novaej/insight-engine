import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from insight_engine.api.deps import get_current_user, get_user_portfolio
from insight_engine.api.schemas import InsightHistoryResponse
from insight_engine.database import get_session
from insight_engine.domain.models import InsightRecord, User

router = APIRouter(prefix="/insights", tags=["insights"])


@router.get("", response_model=InsightHistoryResponse)
async def get_insight_history(
    ticker: str | None = Query(None, min_length=1, max_length=10),
    date_from: datetime.datetime | None = Query(None, alias="from"),
    date_to: datetime.datetime | None = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=500),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Insight history for the user's portfolio, newest first."""
    portfolio = await get_user_portfolio(user, session)
    if portfolio is None:
        return InsightHistoryResponse(total=0, insights=[])

    query = select(InsightRecord).where(InsightRecord.portfolio_id == portfolio.id)
    if ticker:
        query = query.where(InsightRecord.ticker == ticker.upper())
    if date_from:
        query = query.where(InsightRecord.created_at >= date_from)
    if date_to:
        query = query.where(InsightRecord.created_at <= date_to)
    query = query.order_by(InsightRecord.created_at.desc()).limit(limit)

    result = await session.execute(query)
    records = result.scalars().all()

    from insight_engine.api.portfolio_routes import _record_to_response

    return InsightHistoryResponse(
        total=len(records),
        insights=[_record_to_response(r) for r in records],
    )
