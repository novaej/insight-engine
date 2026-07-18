import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from insight_engine.config import settings
from insight_engine.database import get_session
from insight_engine.providers import get_email_provider, get_market_data_provider
from insight_engine.services.monitoring import run_monitoring

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.post("/run")
async def run_monitoring_endpoint(
    x_monitoring_token: str | None = Header(None),
    session: AsyncSession = Depends(get_session),
):
    """Run the monitoring sweep across all alert-enabled users.

    Authorized by the static MONITORING_TOKEN (not a user bearer token) so an
    unattended cron/scheduler can call it.
    """
    if not settings.monitoring_token:
        raise HTTPException(status_code=503, detail="Monitoring is not configured")
    if not x_monitoring_token or not hmac.compare_digest(
        x_monitoring_token, settings.monitoring_token
    ):
        raise HTTPException(status_code=403, detail="Invalid monitoring token")

    summary = await run_monitoring(
        session, get_market_data_provider(), get_email_provider()
    )
    return summary
