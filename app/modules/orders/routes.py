# app/modules/orders/routes.py
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db
from app.modules.auth.routes import get_current_user, RoleChecker
from app.models.auth import User
from app.modules.orders.schemas import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
    OrderListResponse,
)
from app.modules.orders.service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])

admin_or_store_manager = RoleChecker(["Admin", "StoreManager"])
all_authorized = RoleChecker(["Admin", "StoreManager", "Viewer"])


@router.get("", response_model=OrderListResponse)
async def list_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = Query(None, alias="status"),
    store_id: Optional[int] = None,
    customer_id: Optional[int] = None,
    assignment_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(all_authorized),
):
    """Retrieve a paginated list of orders with optional filters."""
    service = OrderService(db)
    orders, total = await service.get_orders(
        skip=skip,
        limit=limit,
        status=status_filter,
        store_id=store_id,
        customer_id=customer_id,
        assignment_status=assignment_status,
    )
    return OrderListResponse(orders=orders, total=total, skip=skip, limit=limit)


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = OrderService(db)
    return await service.place_order(order_data, current_user.id)


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    service = OrderService(db)
    return await service.get_order_by_id(order_id)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(admin_or_store_manager),
):
    """Perform a controlled order status transition. Admin/StoreManager only."""
    service = OrderService(db)
    return await service.update_order_status(
        order_id, status_data.status, user_id=_current_user.id
    )


@router.post("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user)
):
    service = OrderService(db)
    return await service.cancel_order(order_id, user_id=_current_user.id)
