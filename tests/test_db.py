import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from backend.models.orm import Base, Flag

@pytest.mark.asyncio
async def test_flag_table_created():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with engine.connect() as conn:
        result = await conn.execute(
            __import__("sqlalchemy").text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        tables = {row[0] for row in result}
    assert "flags" in tables
    assert "events" in tables
