# app/modules/inventory/service.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientStockException, ResourceNotFoundException, IMSException
from app.core.events import create_outbox_event
from app.models.inventory import InventoryItem, InventoryReservation
from app.modules.inventory.repository import InventoryRepository
from app.modules.inventory.schemas import InventoryItemCreate, InventoryReservationCreate
from app.modules.audit.service import AuditLogService

class InventoryService:
    def __init__(self, db: AsyncSession):
        self.repo = InventoryRepository(db)

    async def get_all_items(self, skip: int = 0, limit: int = 100) -> List[InventoryItem]:
        return await self.repo.get_all_items(skip, limit)

    async def get_items_by_store(self, store_id: int) -> List[InventoryItem]:
        return await self.repo.get_items_by_store(store_id)

    async def add_stock(self, store_id: int, product_id: int, quantity: int, reorder_level: int = 10, user_id: Optional[int] = None) -> InventoryItem:
        """
        Manually adds stock to a store's product inventory.
        Emits inventory.updated and checks if stock is low.
        """
        item = await self.repo.get_item_by_store_and_product_with_lock(store_id, product_id)
        
        old_qty = item.available_quantity if item else 0
        
        if not item:
            item_data = InventoryItemCreate(
                store_id=store_id,
                product_id=product_id,
                available_quantity=quantity,
                reserved_quantity=0,
                reorder_level=reorder_level
            )
            item = await self.repo.create_inventory_item(item_data)
        else:
            item.available_quantity += quantity
            await self.repo.db.flush()

        await AuditLogService(self.repo.db).log_action(
            module="Inventory",
            action="ADD_STOCK",
            user_id=user_id,
            entity_id=str(item.id),
            old_values={"available_quantity": old_qty},
            new_values={"available_quantity": item.available_quantity}
        )

        # Emit outbox event
        await create_outbox_event(
            self.repo.db,
            "inventory.updated",
            {
                "store_id": store_id,
                "product_id": product_id,
                "available_quantity": item.available_quantity,
                "change": quantity
            }
        )

        # Check if still low
        if item.available_quantity <= item.reorder_level:
            await create_outbox_event(
                self.repo.db,
                "inventory.low",
                {
                    "store_id": store_id,
                    "product_id": product_id,
                    "available_quantity": item.available_quantity,
                    "reorder_level": item.reorder_level
                }
            )

        # Commit transactional change and re-retrieve fully-hydrated object to prevent serialization errors [1]
        await self.repo.db.commit()
        refreshed_item = await self.repo.get_item_by_id(item.id)
        if not refreshed_item:
             raise ResourceNotFoundException("Failed to load inventory item after database commit")
             
        return refreshed_item

    async def reserve_stock(self, reservation_data: InventoryReservationCreate, user_id: Optional[int] = None) -> InventoryReservation:
        """
        Reserves inventory items. Implements negative stock prevention and row-level locking.
        Reserving: available_quantity goes down, reserved_quantity goes up.
        """
        store_id = reservation_data.store_id
        product_id = reservation_data.product_id
        quantity = reservation_data.quantity

        # Get inventory item with FOR UPDATE lock
        item = await self.repo.get_item_by_store_and_product_with_lock(store_id, product_id)
        if not item:
            raise ResourceNotFoundException(f"Inventory item not found for store {store_id} and product {product_id}")

        if item.available_quantity < quantity:
            raise IMSException("Insufficient stock available", 400)

        item.available_quantity -= quantity
        item.reserved_quantity += quantity
        await self.repo.db.flush()

        # Generate Reservation
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15) # 15-minute locks
        res = await self.repo.create_reservation(
            store_id=store_id,
            product_id=product_id,
            quantity=quantity,
            expires_at=expires_at,
            order_id=reservation_data.order_id
        )

        await AuditLogService(self.repo.db).log_action(
            module="Inventory",
            action="RESERVE_STOCK",
            user_id=user_id,
            entity_id=str(res.id),
            new_values={"quantity": quantity, "store_id": store_id, "product_id": product_id}
        )

        # Emit inventory.reserved outbox event
        await create_outbox_event(
            self.repo.db,
            "inventory.reserved",
            {
                "reservation_id": res.id,
                "order_id": res.order_id,
                "store_id": store_id,
                "product_id": product_id,
                "quantity": quantity,
                "expires_at": expires_at.isoformat()
            }
        )

        # Check for inventory.low
        if item.available_quantity <= item.reorder_level:
            await create_outbox_event(
                self.repo.db,
                "inventory.low",
                {
                    "store_id": store_id,
                    "product_id": product_id,
                    "available_quantity": item.available_quantity,
                    "reorder_level": item.reorder_level
                }
            )

        # Commit transaction and return refreshed schema [1]
        await self.repo.db.commit()
        refreshed_res = await self.repo.get_reservation_by_id(res.id)
        if not refreshed_res:
            raise ResourceNotFoundException("Failed to load reservation after database commit")
            
        return refreshed_res

    async def confirm_reservation(self, reservation_id: int, user_id: Optional[int] = None) -> InventoryReservation:
        res = await self.repo.get_reservation_by_id_with_lock(reservation_id)
        if not res:
            raise ResourceNotFoundException(f"Reservation {reservation_id} not found")

        if res.status != "PENDING":
            raise IMSException(f"Reservation {reservation_id} is already in state: {res.status}", 400)

        item = await self.repo.get_item_by_store_and_product_with_lock(res.store_id, res.product_id)
        if not item:
            raise ResourceNotFoundException(f"Inventory item not found for store {res.store_id} and product {res.product_id}")

        old_status = res.status
        res.status = "COMPLETED"
        item.reserved_quantity = max(0, item.reserved_quantity - res.quantity)
        await self.repo.db.flush()

        await AuditLogService(self.repo.db).log_action(
            module="Inventory",
            action="CONFIRM_RESERVATION",
            user_id=user_id,
            entity_id=str(res.id),
            old_values={"status": old_status},
            new_values={"status": res.status}
        )

        await create_outbox_event(
            self.repo.db,
            "inventory.updated",
            {
                "store_id": res.store_id,
                "product_id": res.product_id,
                "available_quantity": item.available_quantity,
                "reserved_quantity": item.reserved_quantity,
                "change": 0
            }
        )

        await self.repo.db.commit()
        refreshed_res = await self.repo.get_reservation_by_id(res.id)
        if not refreshed_res:
             raise ResourceNotFoundException("Failed to load reservation after database commit")
             
        return refreshed_res

    async def release_reservation(self, reservation_id: int, status: str = "CANCELLED", user_id: Optional[int] = None) -> InventoryReservation:
        res = await self.repo.get_reservation_by_id_with_lock(reservation_id)
        if not res:
            raise ResourceNotFoundException(f"Reservation {reservation_id} not found")

        if res.status != "PENDING":
            raise IMSException(f"Reservation {reservation_id} is already in state: {res.status}", 400)

        item = await self.repo.get_item_by_store_and_product_with_lock(res.store_id, res.product_id)
        if not item:
            raise ResourceNotFoundException(f"Inventory item not found for store {res.store_id} and product {res.product_id}")

        old_status = res.status
        res.status = status
        item.available_quantity += res.quantity
        item.reserved_quantity = max(0, item.reserved_quantity - res.quantity)
        await self.repo.db.flush()

        await AuditLogService(self.repo.db).log_action(
            module="Inventory",
            action="RELEASE_RESERVATION",
            user_id=user_id,
            entity_id=str(res.id),
            old_values={"status": old_status},
            new_values={"status": res.status}
        )

        await create_outbox_event(
            self.repo.db,
            "inventory.released",
            {
                "reservation_id": res.id,
                "order_id": res.order_id,
                "store_id": res.store_id,
                "product_id": res.product_id,
                "quantity": res.quantity,
                "reason": status
            }
        )

        await self.repo.db.commit()
        refreshed_res = await self.repo.get_reservation_by_id(res.id)
        if not refreshed_res:
             raise ResourceNotFoundException("Failed to load reservation after database commit")
             
        return refreshed_res

    async def release_expired_reservations(self) -> int:
        expired = await self.repo.get_expired_reservations()
        count = 0
        for res in expired:
            try:
                await self.release_reservation(res.id, status="EXPIRED")
                count += 1
            except Exception:
                pass
        return count
        
    async def get_reservations_by_order(self, order_id: str) -> List[InventoryReservation]:
        return await self.repo.get_reservations_by_order(order_id)