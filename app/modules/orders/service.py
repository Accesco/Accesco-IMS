# app/modules/orders/service.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException, IMSException, ForbiddenException
from app.core.events import create_outbox_event
from app.models.order import Order
from app.models.store import Store
from app.models.auth import User
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schemas import OrderCreate
from app.core.geo_utils import haversine_distance, classify_zone_and_sla
from app.modules.audit.service import AuditLogService
from app.modules.websocket.events import publish_event


# Allowed order status transitions. Each key maps to the set of valid next states.
VALID_ORDER_TRANSITIONS = {
    "PENDING": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"READY_FOR_PICKING", "READY_FOR_DISPATCH", "CANCELLED"},
    "READY_FOR_PICKING": {"READY_FOR_DISPATCH", "CANCELLED"},
    "READY_FOR_DISPATCH": {"RIDER_ASSIGNED", "CANCELLED"},
    "RIDER_ASSIGNED": {"DISPATCHED", "CANCELLED"},
    "DISPATCHED": {"PICKED_UP", "CANCELLED", "FAILED"},
    "PICKED_UP": {"IN_TRANSIT", "FAILED"},
    "IN_TRANSIT": {"DELIVERED", "FAILED"},
    "DELIVERED": {"RETURNED"},
    "CANCELLED": set(),
    "FAILED": set(),
    "RETURNED": set(),
}


class OrderService:
    def __init__(self, db: AsyncSession):
        self.repo = OrderRepository(db)

    def _validate_order_access(self, order: Order, current_user: User) -> None:
        """
        Validates that the current user has permission to access the given order.
        - Admin and Store Manager roles can access any order.
        - Customers can only access their own orders.
        - All other cases raise ForbiddenException.
        """
        user_roles = [role.name for role in current_user.roles]

        # Admin and Store Manager can access any order
        if "Admin" in user_roles or "StoreManager" in user_roles:
            return

        # Customers can only access their own orders
        if order.customer_id == current_user.id:
            return

        raise ForbiddenException("You do not have permission to access this order")

    async def get_order_by_id(self, order_id: int, current_user: Optional[User] = None) -> Order:
        order = await self.repo.get_order_by_id(order_id)
        if not order:
            raise ResourceNotFoundException(f"Order with ID {order_id} not found")

        # Enforce ownership if a user context is provided (skipped for internal/system calls)
        if current_user is not None:
            self._validate_order_access(order, current_user)

        return order

    async def get_orders(
        self,
        skip: int = 0,
        limit: int = 50,
        status: Optional[str] = None,
        store_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        assignment_status: Optional[str] = None,
    ) -> Tuple[List[Order], int]:
        """Retrieve paginated and filtered orders."""
        return await self.repo.get_orders(
            skip=skip,
            limit=limit,
            status=status,
            store_id=store_id,
            customer_id=customer_id,
            assignment_status=assignment_status,
        )

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

        # 4. Create outbox event within the same transaction (atomicity fix)
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

        await self.repo.db.commit()

        # 5. Emit real-time event after successful commit
        await publish_event(
            event_type="ORDER_CREATED",
            entity_type="order",
            entity_id=order.id,
            data={
                "order_id": order.id,
                "customer_id": customer_id,
                "store_id": order.store_id,
                "status": order.status,
                "total_amount": float(order.total_amount),
                "delivery_zone": order.delivery_zone,
            },
        )
        
        return order

    async def update_order_status(self, order_id: int, new_status: str, user_id: int = None) -> Order:
        """
        Perform a controlled order status transition with validation.
        Raises IMSException if the transition is not allowed.
        """
        order = await self.repo.get_order_by_id_for_update(order_id)
        if not order:
            raise ResourceNotFoundException(f"Order with ID {order_id} not found")

        old_status = order.status

        # Validate the transition
        allowed = VALID_ORDER_TRANSITIONS.get(old_status, set())
        if new_status not in allowed:
            raise IMSException(
                f"Invalid status transition: {old_status} → {new_status}. "
                f"Allowed transitions: {', '.join(sorted(allowed)) if allowed else 'none (terminal state)'}",
                400,
            )

        await self.repo.update_order_status(order, new_status)

        await AuditLogService(self.repo.db).log_action(
            module="Orders",
            action="UPDATE_ORDER_STATUS",
            user_id=user_id,
            entity_id=str(order.id),
            old_values={"status": old_status},
            new_values={"status": new_status},
        )

        await create_outbox_event(
            self.repo.db,
            "orders.status_changed",
            {
                "order_id": order.id,
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        await self.repo.db.commit()

        # Emit real-time event after successful commit
        await publish_event(
            event_type="ORDER_STATUS_CHANGED",
            entity_type="order",
            entity_id=order.id,
            data={
                "order_id": order.id,
                "old_status": old_status,
                "new_status": new_status,
                "rider_id": order.rider_id,
                "store_id": order.store_id,
            },
        )

        return order

    async def cancel_order(self, order_id: int, user_id: int = None, current_user: Optional[User] = None) -> Order:
        order = await self.get_order_by_id(order_id)

        # Enforce ownership if a user context is provided (skipped for internal/system calls)
        if current_user is not None:
            self._validate_order_access(order, current_user)

        if order.status in ["CANCELLED", "COMPLETED", "DELIVERED", "FAILED"]:
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

        # Create outbox event within the same transaction (atomicity fix)
        await create_outbox_event(
            self.repo.db,
            "orders.cancelled",
            {
                "order_id": order.id,
                "customer_id": order.customer_id
            }
        )

        await self.repo.db.commit()

        # Emit real-time event after successful commit
        await publish_event(
            event_type="ORDER_STATUS_CHANGED",
            entity_type="order",
            entity_id=order.id,
            data={
                "order_id": order.id,
                "old_status": old_status,
                "new_status": "CANCELLED",
                "store_id": order.store_id,
            },
        )
        
        return order

    async def allocate_order(self, order_id: int, user_id: int = None) -> Order:
        """Atomically reserve inventory for all items in an order."""
        order = await self.repo.get_order_by_id_for_update(order_id)
        if not order:
            raise ResourceNotFoundException(f"Order {order_id} not found")
            
        if order.status not in ["CONFIRMED", "PENDING"]:
            raise IMSException(f"Cannot allocate order in status: {order.status}", 400)
            
        from app.modules.inventory.service import InventoryService
        from app.modules.inventory.schemas import InventoryReservationCreate
        
        inventory_service = InventoryService(self.repo.db)
        
        # Idempotency check
        existing = await inventory_service.get_reservations_by_order(str(order.id))
        active_reservations = [r for r in existing if r.status == "PENDING"]
        if active_reservations:
            raise IMSException("Order already has active inventory reservations", 400)
            
        # Allocate all items automatically; if one fails, an exception is raised 
        # and the whole transaction (including previous items) rolls back safely.
        for item in order.items:
            res_data = InventoryReservationCreate(
                store_id=order.store_id,
                product_id=item.product_id,
                quantity=item.quantity,
                order_id=str(order.id),
                expires_in_seconds=600
            )
            await inventory_service.reserve_stock(res_data, user_id=user_id, auto_commit=False)
            
        await AuditLogService(self.repo.db).log_action(
            module="Orders",
            action="ALLOCATE_ORDER",
            user_id=user_id,
            entity_id=str(order.id),
            new_values={"allocated": True}
        )
        
        await self.repo.db.commit()
        return order
        
    async def release_order(self, order_id: int, user_id: int = None) -> Order:
        """Release all inventory reservations for an order."""
        order = await self.repo.get_order_by_id_for_update(order_id)
        if not order:
            raise ResourceNotFoundException(f"Order {order_id} not found")
            
        from app.modules.inventory.service import InventoryService
        inventory_service = InventoryService(self.repo.db)
        
        reservations = await inventory_service.get_reservations_by_order(str(order.id))
        released_count = 0
        for res in reservations:
            if res.status == "PENDING":
                await inventory_service.release_reservation(res.id, status="CANCELLED", user_id=user_id, auto_commit=False)
                released_count += 1
                
        if released_count == 0:
            raise IMSException("No active reservations found for this order", 400)
            
        await AuditLogService(self.repo.db).log_action(
            module="Orders",
            action="RELEASE_ORDER",
            user_id=user_id,
            entity_id=str(order.id),
            new_values={"released_count": released_count}
        )
        
        await self.repo.db.commit()
        return order

    async def confirm_order_payment(self, order_id: int, user_id: int = None) -> Order:
        order = await self.repo.get_order_by_id_for_update(order_id)
        if not order:
            raise ResourceNotFoundException(f"Order {order_id} not found")
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