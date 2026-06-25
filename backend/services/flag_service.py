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
    if data.enabled is not None:
        flag.enabled = data.enabled
    if data.variations is not None:
        flag.variations = data.variations
    if data.default_variation is not None:
        flag.default_variation = data.default_variation
    if data.rules is not None:
        flag.rules = [r.model_dump() for r in data.rules]
    if data.rollout is not None:
        flag.rollout = data.rollout.model_dump()
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
