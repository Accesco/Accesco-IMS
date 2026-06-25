# app/modules/orders/service.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException, IMSException
from app.core.events import create_outbox_event
from app.models.order import Order
from app.models.store import Store
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import OrderCreate
from app.core.geo_utils import haversine_distance, classify_zone_and_sla
from app.modules.audit.service import AuditLogService


class OrderService:
    def __init__(self, db: AsyncSession):
        self.repo = OrderRepository(db)

    async def get_order_by_id(self, order_id: int) -> Order:
        order = await self.repo.get_order_by_id(order_id)
        if not order:
            raise ResourceNotFoundException(f"Order with ID {order_id} not found")
        return order

    async def get_orders_by_customer(self, customer_id: int) -> List[Order]:
        return await self.repo.get_orders_by_customer(customer_id)

    async def place_order(self, order_data: OrderCreate, customer_id: int) -> Order:
        if not order_data.items:
            raise IMSException("Cannot place an order with empty items", 400)
            
        # 1. Fetch Store Coordinates (Section 04)
        result = await self.repo.db.execute(
            select(Store).where(Store.id == order_data.store_id)
        )
        store = result.scalar_one_or_none()
        if not store:
            raise ResourceNotFoundException(f"Store with ID {order_data.store_id} not found")
            
        if store.latitude is None or store.longitude is None:
            raise IMSException("Store does not have coordinates configured", 400)

        # 2. Derive zone and SLA duration using geo-utilities (Section 04)
        dist_km = haversine_distance(store.latitude, store.longitude, order_data.latitude, order_data.longitude)
        delivery_zone, sla_minutes = classify_zone_and_sla(dist_km)
        sla_deadline = datetime.now(timezone.utc) + timedelta(minutes=sla_minutes)

        # 3. Create database entities with computed zone data [1]
        order = await self.repo.create_order(order_data, customer_id, delivery_zone, sla_deadline)
        await self.repo.db.flush()

        await AuditLogService(self.repo.db).log_action(
            module="Orders",
            action="PLACE_ORDER",
            user_id=customer_id,
            entity_id=str(order.id),
            new_values={"total_amount": float(order.total_amount), "store_id": order.store_id}
        )

        await self.repo.db.commit()

        # 4. Prepare Kafka outbox event
        items_payload = [
            {
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": float(item.price)
            }
            for item in order.items
        ]
        
        await create_outbox_event(
            self.repo.db,
            "orders.placed",
            {
                "order_id": order.id,
                "customer_id": customer_id,
                "store_id": order_data.store_id,
                "total_amount": float(order.total_amount),
                "latitude": order.latitude,
                "longitude": order.longitude,
                "delivery_zone": order.delivery_zone,
                "sla_deadline": order.sla_deadline.isoformat(),
                "items": items_payload
            }
        )
        
        return order

    async def cancel_order(self, order_id: int, user_id: int = None) -> Order:
        order = await self.get_order_by_id(order_id)
        if order.status in ["CANCELLED", "COMPLETED"]:
            raise IMSException(f"Order cannot be cancelled in state: {order.status}", 400)
            
        old_status = order.status
        old_payment = order.payment_status

        await self.repo.update_order_status(order, "CANCELLED")
        await self.repo.update_order_payment(order, "REFUNDED")
        await self.repo.db.flush()

        await AuditLogService(self.repo.db).log_action(
            module="Orders",
            action="CANCEL_ORDER",
            user_id=user_id,
            entity_id=str(order.id),
            old_values={"status": old_status, "payment_status": old_payment},
            new_values={"status": "CANCELLED", "payment_status": "REFUNDED"}
        )

        await self.repo.db.commit()

        # Emit orders.cancelled event
        await create_outbox_event(
            self.repo.db,
            "orders.cancelled",
            {
                "order_id": order.id,
                "customer_id": order.customer_id
            }
        )
        
        return order

    async def confirm_order_payment(self, order_id: int, user_id: int = None) -> Order:
        order = await self.get_order_by_id(order_id)
        old_status = order.status
        old_payment = order.payment_status

        await self.repo.update_order_status(order, "CONFIRMED")
        await self.repo.update_order_payment(order, "COMPLETED")
        await self.repo.db.flush()

        await AuditLogService(self.repo.db).log_action(
            module="Orders",
            action="CONFIRM_PAYMENT",
            user_id=user_id,
            entity_id=str(order.id),
            old_values={"status": old_status, "payment_status": old_payment},
            new_values={"status": "CONFIRMED", "payment_status": "COMPLETED"}
        )

        await self.repo.db.commit()
        return order