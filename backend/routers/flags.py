import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.sse_manager import SSEConnectionManager
from backend.deps import get_db, get_sse_manager
from backend.schemas.flag import FlagCreate, FlagResponse, FlagUpdate
from backend.services import flag_service

router = APIRouter(prefix="/api/flags", tags=["flags"])


@router.get("", response_model=list[FlagResponse])
async def list_flags(db: AsyncSession = Depends(get_db)):
    return await flag_service.list_flags(db)


@router.get("/{key}", response_model=FlagResponse)
async def get_flag(key: str, db: AsyncSession = Depends(get_db)):
    return await flag_service.get_flag(db, key)


@router.post("", response_model=FlagResponse, status_code=201)
async def create_flag(
    data: FlagCreate,
    db: AsyncSession = Depends(get_db),
    sse: SSEConnectionManager = Depends(get_sse_manager),
):
    flag = await flag_service.create_flag(db, data)
    await sse.broadcast(flag.key, json.dumps({"event": "created", "key": flag.key}))
    return flag


@router.put("/{key}", response_model=FlagResponse)
async def update_flag(
    key: str,
    data: FlagUpdate,
    db: AsyncSession = Depends(get_db),
    sse: SSEConnectionManager = Depends(get_sse_manager),
):
    flag = await flag_service.update_flag(db, key, data)
    await sse.broadcast(flag.key, json.dumps({"event": "updated", "key": flag.key}))
    return flag


@router.delete("/{key}", status_code=204)
async def delete_flag(
    key: str,
    db: AsyncSession = Depends(get_db),
    sse: SSEConnectionManager = Depends(get_sse_manager),
):
    await flag_service.delete_flag(db, key)
    await sse.broadcast(key, json.dumps({"event": "deleted", "key": key}))
