# app/modules/stores/routes.py
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.modules.auth.routes import RoleChecker, get_current_user
from app.modules.stores.schemas import StoreCreate, StoreUpdate, StoreResponse
from app.modules.stores.service import StoreService

router = APIRouter(prefix="/stores", tags=["stores"])

admin_or_manager = RoleChecker(["Admin", "StoreManager"])
all_authorized = RoleChecker(["Admin", "StoreManager", "ProcurementManager", "InventoryManager", "Viewer"])


@router.post("", response_model=StoreResponse, status_code=status.HTTP_201_CREATED)
async def create_store(
    store_data: StoreCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_manager)
):
    service = StoreService(db)
    return await service.create_store(store_data)


@router.get("", response_model=List[StoreResponse])
async def get_all_stores(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized)
):
    service = StoreService(db)
    return await service.get_all_stores(skip, limit)


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized)
):
    service = StoreService(db)
    return await service.get_store_by_id(store_id)


@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: int,
    update_data: StoreUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_manager)
):
    service = StoreService(db)
    return await service.update_store(store_id, update_data)