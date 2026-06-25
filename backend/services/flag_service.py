from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.orm import Flag
from backend.schemas.flag import FlagCreate, FlagResponse, FlagUpdate


async def list_flags(db: AsyncSession) -> list[FlagResponse]:
    result = await db.execute(select(Flag).order_by(Flag.key))
    return [FlagResponse.model_validate(f) for f in result.scalars()]


async def get_flag(db: AsyncSession, key: str) -> FlagResponse:
    flag = await db.get(Flag, key)
    if flag is None:
        raise HTTPException(status_code=404, detail=f"Flag '{key}' not found")
    return FlagResponse.model_validate(flag)


async def create_flag(db: AsyncSession, data: FlagCreate) -> FlagResponse:
    existing = await db.get(Flag, data.key)
    if existing:
        raise HTTPException(status_code=409, detail=f"Flag '{data.key}' already exists")
    flag = Flag(
        key=data.key,
        enabled=data.enabled,
        variations=data.variations,
        default_variation=data.default_variation,
        rules=[r.model_dump() for r in data.rules],
        rollout=data.rollout.model_dump() if data.rollout else None,
        updated_at=datetime.now(timezone.utc),
    )
    db.add(flag)
    await db.commit()
    await db.refresh(flag)
    return FlagResponse.model_validate(flag)


async def update_flag(db: AsyncSession, key: str, data: FlagUpdate) -> FlagResponse:
    flag = await db.get(Flag, key)
    if flag is None:
        raise HTTPException(status_code=404, detail=f"Flag '{key}' not found")
    fields = data.model_fields_set
    if "enabled" in fields and data.enabled is not None:
        flag.enabled = data.enabled
    if "variations" in fields and data.variations is not None:
        flag.variations = data.variations
    if "default_variation" in fields and data.default_variation is not None:
        flag.default_variation = data.default_variation
    if "rules" in fields:
        flag.rules = [r.model_dump() for r in data.rules] if data.rules is not None else []
    if "rollout" in fields:
        # Explicitly set (even to None) — allows clearing rollout
        flag.rollout = data.rollout.model_dump() if data.rollout else None
    flag.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(flag)
    return FlagResponse.model_validate(flag)


async def delete_flag(db: AsyncSession, key: str) -> None:
    flag = await db.get(Flag, key)
    if flag is None:
        raise HTTPException(status_code=404, detail=f"Flag '{key}' not found")
    await db.delete(flag)
    await db.commit()
