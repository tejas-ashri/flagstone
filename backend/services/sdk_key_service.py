import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.orm import SdkKey

KEY_PREFIX = "fs_"
# Avoid a database write on every SDK poll; last_used_at is only a hint.
LAST_USED_RESOLUTION = timedelta(minutes=5)


def hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def display_prefix(raw: str) -> str:
    return raw[:10]


async def create_key(db: AsyncSession, project_id: str, label: str) -> tuple[SdkKey, str]:
    """Returns the stored row and the raw key, which is not retrievable later."""
    raw = KEY_PREFIX + secrets.token_urlsafe(24)
    row = SdkKey(
        key_hash=hash_key(raw),
        project_id=project_id,
        label=label,
        prefix=display_prefix(raw),
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row, raw


async def list_keys(db: AsyncSession, project_id: str) -> list[SdkKey]:
    result = await db.execute(
        select(SdkKey).where(SdkKey.project_id == project_id).order_by(SdkKey.created_at)
    )
    return list(result.scalars())


async def revoke_key(db: AsyncSession, project_id: str, key_hash: str) -> SdkKey:
    row = await db.get(SdkKey, key_hash)
    if row is None or row.project_id != project_id:
        raise HTTPException(status_code=404, detail="SDK key not found")
    if row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(row)
    return row


async def resolve_key(db: AsyncSession, raw: str) -> SdkKey | None:
    """Returns the active key row for a raw SDK key, or None."""
    row = await db.get(SdkKey, hash_key(raw))
    if row is None or row.revoked_at is not None:
        return None
    now = datetime.now(timezone.utc)
    last = row.last_used_at
    if last is not None and last.tzinfo is None:  # SQLite drops tzinfo
        last = last.replace(tzinfo=timezone.utc)
    if last is None or now - last > LAST_USED_RESOLUTION:
        row.last_used_at = now
        await db.commit()
    return row
