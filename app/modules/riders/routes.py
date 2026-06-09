from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.riders.service import RiderService
from app.modules.riders.schemas import (
    RiderCreate,
    RiderResponse
)

router = APIRouter(
    prefix="/riders",
    tags=["riders"]
)


@router.post("", response_model=RiderResponse)
async def create_rider(
    rider_data: RiderCreate,
    db: AsyncSession = Depends(get_db)
):
    service = RiderService(db)
    return await service.create_rider(rider_data)


@router.get("", response_model=list[RiderResponse])
async def get_riders(
    db: AsyncSession = Depends(get_db)
):
    service = RiderService(db)
    return await service.get_all_riders()