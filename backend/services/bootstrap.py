from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.config import Settings
from backend.models.orm import DEFAULT_PROJECT_ID, Project, SdkKey
from backend.services.sdk_key_service import display_prefix, hash_key


async def ensure_defaults(db: AsyncSession, settings: Settings) -> None:
    """Makes sure the Default project exists and SDK_KEY is one of its keys.

    The key row is only inserted when missing, so revoking it in the UI sticks
    across restarts. Changing SDK_KEY adds a new key; the old one stays active
    until revoked.
    """
    if await db.get(Project, DEFAULT_PROJECT_ID) is None:
        now = datetime.now(timezone.utc)
        db.add(Project(id=DEFAULT_PROJECT_ID, name="Default", created_at=now))
    if settings.sdk_key and await db.get(SdkKey, hash_key(settings.sdk_key)) is None:
        db.add(
            SdkKey(
                key_hash=hash_key(settings.sdk_key),
                project_id=DEFAULT_PROJECT_ID,
                label="Default key (SDK_KEY setting)",
                prefix=display_prefix(settings.sdk_key),
                created_at=datetime.now(timezone.utc),
            )
        )
    await db.commit()


async def run_bootstrap(factory: async_sessionmaker[AsyncSession], settings: Settings) -> None:
    async with factory() as db:
        await ensure_defaults(db, settings)
