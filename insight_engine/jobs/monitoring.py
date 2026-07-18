"""One-off monitoring run: `python -m insight_engine.jobs.monitoring`.

For manual invocation or a cron that runs the module directly instead of calling
the HTTP endpoint. The always-on server also schedules this via APScheduler when
MONITORING_ENABLED is set.
"""

import asyncio
import logging

from insight_engine.database import async_session
from insight_engine.providers import get_email_provider, get_market_data_provider
from insight_engine.services.monitoring import run_monitoring


async def _main() -> None:
    async with async_session() as session:
        summary = await run_monitoring(
            session, get_market_data_provider(), get_email_provider()
        )
    print(f"Monitoring run complete: {summary}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())
