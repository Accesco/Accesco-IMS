# app/modules/dispatch/repository.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.rider import Rider
from app.models.store import Store
from app.models.community import Community
from app.models.batch import Batch
from app.models.outbox import OutboxEvent
from app.core.geo_utils import is_point_in_polygon


async def get_order_for_update(db: AsyncSession, order_id: int) -> Optional[Order]:
    result = await db.execute(
        select(Order).where(Order.id == order_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def get_store_by_id(db: AsyncSession, store_id: int) -> Optional[Store]:
    result = await db.execute(select(Store).where(Store.id == store_id))
    return result.scalar_one_or_none()


async def get_eligible_riders_for_assignment(db: AsyncSession) -> List[Rider]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Rider).where(
            and_(
                Rider.is_available == True,
                Rider.battery_level >= 15.0,
                Rider.shift_end_time > now,
                Rider.last_heartbeat_at >= now - timedelta(seconds=30),
                Rider.status.in_(["IDLE", "BATCHING", "RETURNING"])
            )
        )
    )
    return list(result.scalars().all())


async def get_rider_active_load_count(db: AsyncSession, rider_id: int) -> int:
    result = await db.execute(
        select(Order).where(
            and_(
                Order.rider_id == rider_id,
                Order.status.in_(["PENDING", "ACCEPTED", "PICKING", "DISPATCHED"])
            )
        )
    )
    return len(result.scalars().all())


async def resolve_location_to_community(db: AsyncSession, lat: float, lon: float) -> Optional[Community]:
    result = await db.execute(select(Community))
    communities = result.scalars().all()
    for comm in communities:
        coords = comm.polygon.get("coordinates", [])
        if coords and is_point_in_polygon(lat, lon, coords[0]):
            return comm
    return None


async def get_active_batch_for_community(db: AsyncSession, community_id: str) -> Optional[Batch]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.orders))
        .where(
            and_(
                Batch.community_id == community_id,
                Batch.status == "DRAFT",
                Batch.dispatch_by > now
            )
        )
    )
    return result.scalar_one_or_none()


async def create_batch(db: AsyncSession, community_id: str, dispatch_by: datetime) -> Batch:
    new_batch = Batch(
        community_id=community_id,
        status="DRAFT",
        dispatch_by=dispatch_by
    )
    db.add(new_batch)
    await db.flush()
    return new_batch


async def get_batch_by_id_for_update(db: AsyncSession, batch_id: int) -> Optional[Batch]:
    """
    Acquires transactional row lock and eagerly loads orders to prevent lazy loading [1].
    """
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.orders)) # Eagerly load the orders list to prevent lazy-loading [1]
        .where(Batch.id == batch_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def get_batch_by_id_with_orders(db: AsyncSession, batch_id: int) -> Optional[Batch]:
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.orders))
        .where(Batch.id == batch_id)
    )
    return result.scalar_one_or_none()


async def get_all_active_batches(db: AsyncSession) -> List[Batch]:
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.orders))
        .where(Batch.status.in_(["DRAFT", "OFFERED", "ASSIGNED"]))
    )
    return list(result.scalars().all())


async def get_hourly_order_rate_for_community(db: AsyncSession, community_id: str) -> int:
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    result = await db.execute(
        select(Order).where(
            and_(
                Order.community_id == community_id,
                Order.created_at >= one_hour_ago
            )
        )
    )
    return len(result.scalars().all())


async def create_outbox_event(db: AsyncSession, event_type: str, payload: dict):
    event = OutboxEvent(
        event_type=event_type,
        payload=payload,
        status="PENDING"
    )
    db.add(event)
    await db.flush()


async def assign_rider_to_order(db: AsyncSession, order: Order, rider: Rider):
    order.rider_id = rider.id
    order.assignment_status = "ASSIGNED"
    rider.is_available = False
    rider.status = "ASSIGNED"
    await db.commit()
    await db.refresh(order)
    return order