# app/modules/orders/repository.py
from __future__ import annotations

from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem
from app.modules.orders.schemas import OrderCreate

class OrderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def get_orders_by_customer(self, customer_id: int) -> List[Order]:
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.customer_id == customer_id)
        )
        return list(result.scalars().all())

    async def create_order(
        self, 
        order_data: OrderCreate, 
        customer_id: int, 
        delivery_zone: str, 
        sla_deadline: datetime
    ) -> Order:
        total = sum(item.price * item.quantity for item in order_data.items)
        
        # Populate all required Phase 2 Database Columns during order creation [1]
        db_order = Order(
            customer_id=customer_id,
            store_id=order_data.store_id,
            status="PENDING",
            total_amount=total,
            payment_status="PENDING",
            latitude=order_data.latitude,
            longitude=order_data.longitude,
            delivery_zone=delivery_zone,
            sla_deadline=sla_deadline,
            assignment_status="UNASSIGNED"
        )
        self.db.add(db_order)
        await self.db.flush()

        for item in order_data.items:
            db_item = OrderItem(
                order_id=db_order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price
            )
            self.db.add(db_item)
            
        await self.db.flush()

        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == db_order.id)
        )
        return result.scalar_one()

    async def update_order_status(self, order: Order, status: str) -> Order:
        order.status = status
        await self.db.flush()
        return order

    async def update_order_payment(self, order: Order, payment_status: str) -> Order:
        order.payment_status = payment_status
        await self.db.flush()
        return order