from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.config import get_settings
from backend.db.session import make_engine, session_factory
from backend.db.sse_manager import SSEConnectionManager
from backend.routers.analytics import router as analytics_router
from backend.routers.flags import router as flags_router
from backend.routers.sdk import router as sdk_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    engine = make_engine(settings.database_url)
    app.state.db_engine = engine
    app.state.session_factory = session_factory(engine)
    app.state.sse_manager = SSEConnectionManager()
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(title="Flagstone", lifespan=lifespan)
    app.include_router(flags_router)
    app.include_router(sdk_router)
    app.include_router(analytics_router)
    return app


app = create_app()
