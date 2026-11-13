import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from backend.db.sse_manager import SSEConnectionManager
from backend.deps import get_db, get_sse_manager
from backend.routers.flags import project_channel
from backend.schemas.event import EventBatch
from backend.services import analytics_service, flag_service, sdk_key_service

router = APIRouter(prefix="/sdk", tags=["sdk"])


async def _verify_sdk_key(
    x_sdk_key: str = Header(...), db: AsyncSession = Depends(get_db)
) -> str:
    """Returns the project the key belongs to. An SDK key only ever sees and
    writes data of its own project."""
    key = await sdk_key_service.resolve_key(db, x_sdk_key)
    if key is None:
        raise HTTPException(status_code=401, detail="Invalid SDK key")
    return key.project_id


@router.get("/config")
async def sdk_config(
    db: AsyncSession = Depends(get_db),
    project_id: str = Depends(_verify_sdk_key),
):
    flags = await flag_service.list_flags(db, project_id)
    return {
        "flags": {f.key: f.model_dump() for f in flags},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/stream")
async def sse_stream(
    request: Request,
    manager: SSEConnectionManager = Depends(get_sse_manager),
    project_id: str = Depends(_verify_sdk_key),
):
    channel = project_channel(project_id)
    queue = await manager.subscribe(channel)

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
            await manager.unsubscribe(channel, queue)

    return EventSourceResponse(event_generator())


@router.post("/events", status_code=202)
async def ingest_events(
    batch: EventBatch,
    db: AsyncSession = Depends(get_db),
    project_id: str = Depends(_verify_sdk_key),
):
    # Events for flags outside this key's project (or deleted flags) are
    # dropped rather than failing the whole batch.
    known = await flag_service.flag_keys(db, project_id)
    accepted = [e for e in batch.events if e.flag_key in known]
    await analytics_service.insert_events(db, project_id, accepted)
    return {"accepted": len(accepted), "rejected": len(batch.events) - len(accepted)}
