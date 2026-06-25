from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.sse_manager import SSEConnectionManager


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


def get_sse_manager(request: Request) -> SSEConnectionManager:
    return request.app.state.sse_manager
