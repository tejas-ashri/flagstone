import httpx
import pytest_asyncio
from backend.config import Settings, get_settings
from backend.db.sse_manager import SSEConnectionManager
from backend.models.orm import DEFAULT_PROJECT_ID, Base
from backend.services import auth_service
from backend.services.auth_service import Profile
from backend.services.bootstrap import ensure_defaults
from sqlalchemy.ext.asyncio import create_async_engine

CSRF = {"X-Requested-With": "flagstone"}


@pytest_asyncio.fixture
async def engine():
    e = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield e
    await e.dispose()


@pytest_asyncio.fixture
async def app(engine):
    from backend.db.session import session_factory
    from backend.main import create_app

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

    # The test transport doesn't run the lifespan, so seed what startup would.
    async with app.state.session_factory() as db:
        await ensure_defaults(db, get_settings())
    return app


async def sign_in_as(app, email: str, default_role: str | None = None) -> str:
    """Creates a user (optionally a member of the Default project) and returns
    a session token for them."""
    settings = Settings(admin_emails="")
    async with app.state.session_factory() as db:
        user = await auth_service.sign_in(
            db, Profile("dev", email, email, email_verified=True), settings
        )
        if default_role:
            await auth_service._grant(db, DEFAULT_PROJECT_ID, user.id, default_role)
            await db.commit()
        return await auth_service.create_session(db, user.id, settings)


def make_client(app, token: str | None = None) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
        headers=CSRF,
        cookies={"flagstone_session": token} if token else None,
    )


@pytest_asyncio.fixture
async def client(app):
    """Signed in as an admin of the Default project, which the original
    /api/flags and /api/experiments paths act on."""
    token = await sign_in_as(app, "admin@example.com", default_role="admin")
    async with make_client(app, token) as c:
        yield c


@pytest_asyncio.fixture
async def anon_client(app):
    async with make_client(app) as c:
        yield c
