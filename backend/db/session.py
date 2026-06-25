from collections.abc import AsyncIterator
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


def make_engine(dsn: str) -> AsyncEngine:
    return create_async_engine(dsn, poolclass=NullPool)


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_db(request) -> AsyncIterator[AsyncSession]:  # overridden in deps.py
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session
