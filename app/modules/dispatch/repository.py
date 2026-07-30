# app/modules/dispatch/repository.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.rider import Rider
from app.models.store import Store
from app.models.community import Community
from app.models.batch import Batch
from app.models.outbox import OutboxEvent
from app.models.forecast import ForecastMetric, CommunityDynamicWindow
from app.models.dispatch_latency import DispatchLatencySample
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
    """
    Retrieves the active draft batch for a community, evaluating
    expiration times in a timezone-safe manner [1].
    """
    # 1. Query active draft batches for this community
    result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.orders)) 
        .where(
            and_(
                Batch.community_id == community_id,
                Batch.status == "DRAFT"
            )
        )
    )
    active_batches = result.scalars().all()

    # 2. Perform timezone-safe expiration check 
    now = datetime.now(timezone.utc)

    for batch in active_batches:
        # Normalize batch.dispatch_by to timezone-aware UTC for safe comparison [1]
        dispatch_by = batch.dispatch_by
        if dispatch_by.tzinfo is None:
            dispatch_by = dispatch_by.replace(tzinfo=timezone.utc)

        if dispatch_by > now:
            return batch

    return None


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
        .options(selectinload(Batch.orders))  # Eagerly load the orders list to prevent lazy-loading [1]
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


async def get_store_id_for_community(db: AsyncSession, community_id: str) -> Optional[int]:
    """
    Looks up the most recent order's store_id for a given community.
    Used by BatchWindowOptimizer to populate ForecastMetric.store_id.
    Returns None if no orders exist for the community yet.
    """
    result = await db.execute(
        select(Order.store_id)
        .where(Order.community_id == community_id)
        .order_by(Order.id.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def create_forecast_metric(
    db: AsyncSession,
    store_id: int,
    target_time: datetime,
    predicted_orders_per_min: float,
    predicted_rider_demand: int,
    predicted_batch_size: float,
    recommended_batch_window_sec: int,
) -> ForecastMetric:
    """
   "Persists a ForecastMetric row after each batch window calculation."
    Allows ops to validate Holt-Winters accuracy against MAPE targets.
    """
    metric = ForecastMetric(
        store_id=store_id,
        target_time=target_time,
        predicted_orders_per_min=predicted_orders_per_min,
        predicted_rider_demand=predicted_rider_demand,
        predicted_batch_size=predicted_batch_size,
        recommended_batch_window_sec=recommended_batch_window_sec,
    )
    db.add(metric)
    await db.flush()
    return metric


async def create_community_dynamic_window(
    db: AsyncSession,
    community_id: str,
    hour_of_day: int,
    day_of_week: int,
    order_velocity_weight: float,
    calculated_window_sec: int,
) -> CommunityDynamicWindow:
    """
    "Persists a CommunityDynamicWindow row for historical window analysis."
    """
    window = CommunityDynamicWindow(
        community_id=community_id,
        hour_of_day=hour_of_day,
        day_of_week=day_of_week,
        order_velocity_weight=order_velocity_weight,
        calculated_window_sec=calculated_window_sec,
    )
    db.add(window)
    await db.flush()
    return window



async def record_latency_sample(db: AsyncSession, path: str, duration_ms: float) -> None:
    """Appends a single latency observation for P50/P95/P99 computation."""
    sample = DispatchLatencySample(path=path, duration_ms=duration_ms)
    db.add(sample)
    await db.flush()


async def get_latency_percentiles(
    db: AsyncSession, path: str, window_minutes: int = 60
) -> dict:
    """
    Computes P50/P95/P99 for the given path over the last window_minutes.
    Returns a dict with p50, p95, p99 keys (in milliseconds).
    """
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    result = await db.execute(
        select(DispatchLatencySample.duration_ms)
        .where(
            and_(
                DispatchLatencySample.path == path,
                DispatchLatencySample.created_at >= since,
            )
        )
        .order_by(DispatchLatencySample.duration_ms)
    )
    samples = [row[0] for row in result.fetchall()]
    if not samples:
        return {"p50": None, "p95": None, "p99": None, "sample_count": 0}

    n = len(samples)

    def percentile(p: float) -> float:
        idx = int(p / 100 * (n - 1))
        return round(samples[idx], 2)

    return {
        "p50": percentile(50),
        "p95": percentile(95),
        "p99": percentile(99),
        "sample_count": n,
    }



async def get_order_count_for_community_window(
    db: AsyncSession, community_id: str, since: datetime, until: datetime
) -> int:
    """Returns the count of orders for a community between two timestamps."""
    result = await db.execute(
        select(func.count(Order.id)).where(
            and_(
                Order.community_id == community_id,
                Order.created_at >= since,
                Order.created_at < until,
            )
        )
    )
    return int(result.scalar() or 0)