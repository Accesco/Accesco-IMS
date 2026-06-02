from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.modules.auth.routes import RoleChecker
from app.modules.inventory.schemas import (
    InventoryItemResponse,
    InventoryReservationCreate,
    InventoryReservationResponse
)
from app.modules.inventory.service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])

# Roles
admin_or_inv_manager = RoleChecker(["Admin", "StoreManager", "InventoryManager"])
all_authorized = RoleChecker(["Admin", "StoreManager", "ProcurementManager", "InventoryManager", "Viewer"])


@router.get("", response_model=List[InventoryItemResponse])
async def get_inventory(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized)
):
    service = InventoryService(db)
    return await service.get_all_items(skip, limit)


@router.get("/store/{store_id}", response_model=List[InventoryItemResponse])
async def get_store_inventory(
    store_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized)
):
    service = InventoryService(db)
    return await service.get_items_by_store(store_id)


@router.post("/add-stock", response_model=InventoryItemResponse)
async def add_stock(
    store_id: int,
    product_id: int,
    quantity: int,
    reorder_level: int = 10,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_inv_manager)
):
    service = InventoryService(db)
    return await service.add_stock(store_id, product_id, quantity, reorder_level)


@router.post("/reserve", response_model=InventoryReservationResponse, status_code=status.HTTP_201_CREATED)
async def reserve_stock(
    reservation_data: InventoryReservationCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized)
):
    service = InventoryService(db)
    return await service.reserve_stock(reservation_data)


@router.post("/release/{reservation_id}", response_model=InventoryReservationResponse)
async def release_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_inv_manager)
):
    service = InventoryService(db)
    return await service.release_reservation(reservation_id)
