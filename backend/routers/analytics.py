from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.deps import get_db
from backend.services import analytics_service, flag_service
from backend.schemas.event import ExperimentResults

router = APIRouter(prefix="/api/experiments", tags=["analytics"])


@router.get("/{key}/results", response_model=ExperimentResults)
async def experiment_results(key: str, db: AsyncSession = Depends(get_db)):
    # Raises 404 if flag doesn't exist
    await flag_service.get_flag(db, key)
    return await analytics_service.get_experiment_results(db, key)
