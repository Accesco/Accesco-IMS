# app/modules/riders/routes.py
from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.routes import RoleChecker
from app.modules.riders.service import RiderService
from app.modules.riders.schemas import (
    RiderCreate,
    RiderUpdate,
    RiderResponse
)

router = APIRouter(
    prefix="/riders",
    tags=["riders"]
)

admin_or_store_manager = RoleChecker(["Admin", "StoreManager"])
all_authorized = RoleChecker(["Admin", "StoreManager", "Viewer"])


@router.post("", response_model=RiderResponse)
async def create_rider(
    rider_data: RiderCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager)
):
    service = RiderService(db)
    return await service.create_rider(rider_data)


@router.get("", response_model=List[RiderResponse])
async def get_riders(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized)
):
    service = RiderService(db)
    return await service.get_all_riders()


@router.get("/{rider_id}", response_model=RiderResponse)
async def get_rider(
    rider_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized)
):
    service = RiderService(db)
    return await service.get_rider(rider_id)


@router.put("/{rider_id}", response_model=RiderResponse)
async def update_rider(
    rider_id: int,
    rider_data: RiderUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager)
):
    service = RiderService(db)
    return await service.update_rider(rider_id, rider_data)


@router.delete("/{rider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rider(
    rider_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager)
):
    service = RiderService(db)
    await service.delete_rider(rider_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)