import logging
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI

try:
    # Single source of truth: the version lives in pyproject.toml.
    __version__ = _pkg_version("insight-engine")
except PackageNotFoundError:  # running from a raw checkout without an install
    __version__ = "0.0.0"

from insight_engine.api.asset_routes import router as asset_router
from insight_engine.api.insight_routes import router as insight_router
from insight_engine.api.monitoring_routes import router as monitoring_router
from insight_engine.api.portfolio_routes import router as portfolio_router
from insight_engine.api.position_routes import router as position_router
from insight_engine.api.profile_routes import router as profile_router
from insight_engine.api.user_routes import router as user_router
from insight_engine.config import settings

logger = logging.getLogger(__name__)


async def _scheduled_monitoring() -> None:
    """Scheduler entrypoint: run the monitoring sweep in its own session."""
    from insight_engine.database import async_session
    from insight_engine.providers import get_email_provider, get_market_data_provider
    from insight_engine.services.monitoring import run_monitoring

    async with async_session() as session:
        summary = await run_monitoring(
            session, get_market_data_provider(), get_email_provider()
        )
    logger.info("Scheduled monitoring run: %s", summary)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler: AsyncIOScheduler | None = None
    if settings.monitoring_enabled:
        # Single-process only: run one scheduler instance (uvicorn --workers 1
        # or a dedicated process) so alerts don't double-send.
        scheduler = AsyncIOScheduler()
        scheduler.add_job(
            _scheduled_monitoring,
            CronTrigger.from_crontab(settings.monitoring_cron),
            id="monitoring",
        )
        scheduler.start()
        logger.info("Monitoring scheduler started (cron: %s)", settings.monitoring_cron)
    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown(wait=False)


app = FastAPI(
    title="InsightEngine",
    description="Educational investment portfolio analysis API",
    version=__version__,
    lifespan=lifespan,
)

app.include_router(user_router)
app.include_router(asset_router)
app.include_router(portfolio_router)
app.include_router(position_router)
app.include_router(insight_router)
app.include_router(profile_router)
app.include_router(monitoring_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
