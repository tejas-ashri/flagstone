from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.orm import Flag
from backend.schemas.flag import FlagCreate, FlagResponse, FlagUpdate


async def _load(db: AsyncSession, project_id: str, key: str) -> Flag:
    flag = await db.get(Flag, {"project_id": project_id, "key": key})
    if flag is None:
        raise HTTPException(status_code=404, detail=f"Flag '{key}' not found")
    return flag


async def list_flags(db: AsyncSession, project_id: str) -> list[FlagResponse]:
    result = await db.execute(
        select(Flag).where(Flag.project_id == project_id).order_by(Flag.key)
    )
    return [FlagResponse.model_validate(f) for f in result.scalars()]


async def flag_keys(db: AsyncSession, project_id: str) -> set[str]:
    result = await db.execute(select(Flag.key).where(Flag.project_id == project_id))
    return set(result.scalars())


async def get_flag(db: AsyncSession, project_id: str, key: str) -> FlagResponse:
    return FlagResponse.model_validate(await _load(db, project_id, key))


async def create_flag(db: AsyncSession, project_id: str, data: FlagCreate) -> FlagResponse:
    existing = await db.get(Flag, {"project_id": project_id, "key": data.key})
    if existing:
        raise HTTPException(status_code=409, detail=f"Flag '{data.key}' already exists")
    flag = Flag(
        project_id=project_id,
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


async def update_flag(
    db: AsyncSession, project_id: str, key: str, data: FlagUpdate
) -> FlagResponse:
    flag = await _load(db, project_id, key)
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


async def delete_flag(db: AsyncSession, project_id: str, key: str) -> None:
    flag = await _load(db, project_id, key)
    await db.delete(flag)
    await db.commit()
