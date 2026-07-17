from contextlib import asynccontextmanager

from fastapi import FastAPI

from insight_engine.api.asset_routes import router as asset_router
from insight_engine.api.insight_routes import router as insight_router
from insight_engine.api.portfolio_routes import router as portfolio_router
from insight_engine.api.position_routes import router as position_router
from insight_engine.api.profile_routes import router as profile_router
from insight_engine.api.user_routes import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="InsightEngine",
    description="Educational investment portfolio analysis API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(user_router)
app.include_router(asset_router)
app.include_router(portfolio_router)
app.include_router(position_router)
app.include_router(insight_router)
app.include_router(profile_router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
