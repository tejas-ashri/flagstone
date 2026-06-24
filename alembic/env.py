import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from backend.models.orm import Base
from backend.config import get_settings

config = context.config
target_metadata = Base.metadata

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def run_migrations_online():
    settings = get_settings()
    connectable = create_async_engine(settings.database_url)

    async def do_run():
        async with connectable.connect() as connection:
            await connection.run_sync(
                lambda sync_conn: context.configure(
                    connection=sync_conn, target_metadata=target_metadata
                )
            )
            async with connection.begin():
                await connection.run_sync(lambda c: context.run_migrations())

    asyncio.run(do_run())


run_migrations_online()
