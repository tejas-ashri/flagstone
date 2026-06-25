import pytest
import pytest_asyncio
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.models.orm import Base
from backend.db.sse_manager import SSEConnectionManager


@pytest_asyncio.fixture
async def engine():
    e = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    await e.dispose()


@pytest_asyncio.fixture
async def client(engine):
    from backend.main import create_app
    from backend.db.session import session_factory

    app = create_app()
    app.state.db_engine = engine
    app.state.session_factory = session_factory(engine)
    app.state.sse_manager = SSEConnectionManager()

    from backend.deps import get_db

    async def override_get_db():
        factory = app.state.session_factory
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
