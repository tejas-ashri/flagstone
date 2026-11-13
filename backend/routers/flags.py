import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.sse_manager import SSEConnectionManager
from backend.deps import ProjectAccess, get_db, get_sse_manager, project_admin, project_viewer
from backend.schemas.flag import FlagCreate, FlagResponse, FlagUpdate
from backend.schemas.project import EvaluateRequest, EvaluateResponse
from backend.services import flag_service
from backend.services.explain import explain

# Mounted under /api/projects/{project_id} and, for the Default project, /api.
router = APIRouter(prefix="/flags", tags=["flags"])


def project_channel(project_id: str) -> str:
    return f"project:{project_id}"


async def _notify(sse: SSEConnectionManager, project_id: str, event: str, key: str) -> None:
    try:
        await sse.broadcast(project_channel(project_id), json.dumps({"event": event, "key": key}))
    except Exception:
        pass


@router.get("", response_model=list[FlagResponse])
async def list_flags(
    access: ProjectAccess = Depends(project_viewer), db: AsyncSession = Depends(get_db)
):
    return await flag_service.list_flags(db, access.project_id)


@router.get("/{key}", response_model=FlagResponse)
async def get_flag(
    key: str, access: ProjectAccess = Depends(project_viewer), db: AsyncSession = Depends(get_db)
):
    return await flag_service.get_flag(db, access.project_id, key)


@router.post("", response_model=FlagResponse, status_code=201)
async def create_flag(
    data: FlagCreate,
    access: ProjectAccess = Depends(project_admin),
    db: AsyncSession = Depends(get_db),
    sse: SSEConnectionManager = Depends(get_sse_manager),
):
    flag = await flag_service.create_flag(db, access.project_id, data)
    await _notify(sse, access.project_id, "created", flag.key)
    return flag


@router.put("/{key}", response_model=FlagResponse)
async def update_flag(
    key: str,
    data: FlagUpdate,
    access: ProjectAccess = Depends(project_admin),
    db: AsyncSession = Depends(get_db),
    sse: SSEConnectionManager = Depends(get_sse_manager),
):
    flag = await flag_service.update_flag(db, access.project_id, key, data)
    await _notify(sse, access.project_id, "updated", flag.key)
    return flag


@router.delete("/{key}", status_code=204)
async def delete_flag(
    key: str,
    access: ProjectAccess = Depends(project_admin),
    db: AsyncSession = Depends(get_db),
    sse: SSEConnectionManager = Depends(get_sse_manager),
):
    await flag_service.delete_flag(db, access.project_id, key)
    await _notify(sse, access.project_id, "deleted", key)


@router.post("/{key}/evaluate", response_model=EvaluateResponse)
async def evaluate_flag(
    key: str,
    body: EvaluateRequest,
    access: ProjectAccess = Depends(project_viewer),
    db: AsyncSession = Depends(get_db),
):
    flag = (await flag_service.get_flag(db, access.project_id, key)).model_dump()
    try:
        result = explain(flag, body.user)
        value = flag["variations"][result["variation_index"]]
    except (TypeError, IndexError, KeyError) as e:
        # The same error would crash the SDK, so surface it to the admin.
        raise HTTPException(
            status_code=422, detail=f"This flag's configuration cannot be evaluated: {e}"
        ) from e
    return EvaluateResponse(value=value, **result)
