from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.deps import ProjectAccess, get_db, project_viewer
from backend.schemas.event import ExperimentResults
from backend.services import analytics_service, flag_service

# Mounted under /api/projects/{project_id} and, for the Default project, /api.
router = APIRouter(prefix="/experiments", tags=["analytics"])


@router.get("/{key}/results", response_model=ExperimentResults)
async def experiment_results(
    key: str, access: ProjectAccess = Depends(project_viewer), db: AsyncSession = Depends(get_db)
):
    # Raises 404 if flag doesn't exist
    await flag_service.get_flag(db, access.project_id, key)
    return await analytics_service.get_experiment_results(db, access.project_id, key)
