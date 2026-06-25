import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.sse_manager import SSEConnectionManager
from backend.deps import get_db, get_sse_manager
from backend.schemas.event import EventBatch
from backend.services import analytics_service, flag_service

router = APIRouter(prefix="/sdk", tags=["sdk"])


async def _verify_sdk_key(x_sdk_key: str = Header(...)):
    # v1: single static key from config. The sdk_keys table exists for v2
    # revocable keys but is not yet wired — all clients share one key.
    from backend.config import get_settings
    if x_sdk_key != get_settings().sdk_key:
        raise HTTPException(status_code=401, detail="Invalid SDK key")
    return x_sdk_key


@router.get("/config")
async def sdk_config(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(_verify_sdk_key),
):
    flags = await flag_service.list_flags(db)
    return {
        "flags": {f.key: f.model_dump() for f in flags},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/stream")
async def sse_stream(
    request: Request,
    manager: SSEConnectionManager = Depends(get_sse_manager),
    _: str = Depends(_verify_sdk_key),
):
    queue = await manager.subscribe("*")

    async def event_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {"event": "flag_updated", "data": data}
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": ""}
        finally:
            await manager.unsubscribe("*", queue)

    return EventSourceResponse(event_generator())


@router.post("/events", status_code=202)
async def ingest_events(
    batch: EventBatch,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(_verify_sdk_key),
):
    await analytics_service.insert_events(db, batch.events)
    return {"accepted": len(batch.events)}
