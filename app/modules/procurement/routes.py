from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.modules.auth.routes import RoleChecker
from app.modules.procurement.schemas import PurchaseOrderCreate, PurchaseOrderResponse
from app.modules.procurement.service import ProcurementService

router = APIRouter(prefix="/procurement", tags=["procurement"])

# Role permission helpers
admin_or_procurement = RoleChecker(["Admin", "ProcurementManager"])


@router.post("/purchase-orders", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    po_data: PurchaseOrderCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_procurement)
):
    service = ProcurementService(db)
    return await service.create_purchase_order(po_data)


@router.get("/purchase-orders", response_model=List[PurchaseOrderResponse])
async def get_all_purchase_orders(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_procurement)
):
    service = ProcurementService(db)
    return await service.get_all_purchase_orders(skip, limit)


@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderResponse)
async def get_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_procurement)
):
    service = ProcurementService(db)
    return await service.get_purchase_order_by_id(po_id)


@router.post("/purchase-orders/{po_id}/receive", response_model=PurchaseOrderResponse)
async def receive_purchase_order(
    po_id: int,
    store_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_procurement)
):
    service = ProcurementService(db)
    return await service.receive_purchase_order(po_id, store_id)
