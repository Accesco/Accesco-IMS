# app/modules/inventory/repository.py
from __future__ import annotations

from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.inventory import InventoryItem, InventoryReservation
from app.modules.inventory.schemas import InventoryItemCreate


class InventoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_item_by_id(self, item_id: int) -> Optional[InventoryItem]:
        result = await self.db.execute(
            select(InventoryItem)
            .options(selectinload(InventoryItem.store), selectinload(InventoryItem.product))
            .where(InventoryItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_item_by_store_and_product(self, store_id: int, product_id: int) -> Optional[InventoryItem]:
        result = await self.db.execute(
            select(InventoryItem)
            .options(selectinload(InventoryItem.store), selectinload(InventoryItem.product))
            .where(
                InventoryItem.store_id == store_id,
                InventoryItem.product_id == product_id
            )
        )
        return result.scalar_one_or_none()

    async def get_item_by_store_and_product_with_lock(self, store_id: int, product_id: int) -> Optional[InventoryItem]:
        result = await self.db.execute(
            select(InventoryItem)
            .options(selectinload(InventoryItem.store), selectinload(InventoryItem.product))
            .where(
                InventoryItem.store_id == store_id,
                InventoryItem.product_id == product_id
            )
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_all_items(self, skip: int = 0, limit: int = 100) -> List[InventoryItem]:
        result = await self.db.execute(
            select(InventoryItem)
            .options(selectinload(InventoryItem.store), selectinload(InventoryItem.product))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_items_by_store(self, store_id: int) -> List[InventoryItem]:
        result = await self.db.execute(
            select(InventoryItem)
            .options(selectinload(InventoryItem.store), selectinload(InventoryItem.product))
            .where(InventoryItem.store_id == store_id)
        )
        return list(result.scalars().all())

    async def create_inventory_item(self, item_data: InventoryItemCreate) -> InventoryItem:
        db_item = InventoryItem(
            store_id=item_data.store_id,
            product_id=item_data.product_id,
            available_quantity=item_data.available_quantity,
            reserved_quantity=item_data.reserved_quantity,
            reorder_level=item_data.reorder_level
        )
        self.db.add(db_item)
        await self.db.flush()
        return db_item

    async def get_reservation_by_id(self, res_id: int) -> Optional[InventoryReservation]:
        result = await self.db.execute(
            select(InventoryReservation)
            .options(selectinload(InventoryReservation.store), selectinload(InventoryReservation.product))
            .where(InventoryReservation.id == res_id)
        )
        return result.scalar_one_or_none()

    async def get_reservation_by_id_with_lock(self, res_id: int) -> Optional[InventoryReservation]:
        result = await self.db.execute(
            select(InventoryReservation)
            .options(selectinload(InventoryReservation.store), selectinload(InventoryReservation.product))
            .where(InventoryReservation.id == res_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def create_reservation(
        self, store_id: int, product_id: int, quantity: int, expires_at: datetime, order_id: Optional[str] = None
    ) -> InventoryReservation:
        res = InventoryReservation(
            store_id=store_id,
            product_id=product_id,
            quantity=quantity,
            expires_at=expires_at,
            order_id=order_id,
            status="PENDING"
        )
        self.db.add(res)
        await self.db.flush()
        return res

    async def get_expired_reservations(self) -> List[InventoryReservation]:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(InventoryReservation)
            .options(selectinload(InventoryReservation.store), selectinload(InventoryReservation.product))
            .where(
                InventoryReservation.status == "PENDING",
                InventoryReservation.expires_at <= now
            )
        )
        return list(result.scalars().all())
        
    async def get_reservations_by_order(self, order_id: str) -> List[InventoryReservation]:
        result = await self.db.execute(
            select(InventoryReservation)
            .options(selectinload(InventoryReservation.store), selectinload(InventoryReservation.product))
            .where(InventoryReservation.order_id == order_id)
        )
        return list(result.scalars().all())