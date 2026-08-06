# app/modules/dispatch/service.py
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import ResourceNotFoundException, IMSException
from app.core.geo_utils import (
    haversine_distance,
    optimize_drops,
    classify_zone_and_sla,
    calculate_rae_score
)
from app.modules.dispatch import repository


from app.models.rider import Rider
from app.models.order import Order
from app.models.batch import Batch
from app.models.community import Community
from app.models.store import Store

logger = logging.getLogger("dispatch_engine")
logger.setLevel(logging.INFO)


VALID_TRANSITIONS = {
    "IDLE": ["ASSIGNED", "OFFLINE"],
    "ASSIGNED": ["EN_ROUTE_PICKUP", "IDLE", "OFFLINE"],
    "EN_ROUTE_PICKUP": ["DELIVERING", "IDLE", "OFFLINE"],
    "DELIVERING": ["RETURNING", "OFFLINE"],
    "RETURNING": ["BATCHING", "IDLE", "OFFLINE"],
    "BATCHING": ["DELIVERING", "IDLE", "OFFLINE"],
    "OFFLINE": ["IDLE"]
}


def validate_state_transition(from_state: str, to_state: str) -> bool:
    if from_state == to_state:
        return True
    return to_state in VALID_TRANSITIONS.get(from_state, [])


async def update_rider_state(db: AsyncSession, rider: Rider, target_state: str, trigger: str):
    if not validate_state_transition(rider.status, target_state):
        raise IMSException(f"Invalid state transition: {rider.status} -> {target_state}", 400)

    old_state = rider.status
    rider.status = target_state

    await repository.create_outbox_event(
        db,
        "RIDER_STATE_TRANSITION",
        {
            "rider_id": rider.id,
            "old_state": old_state,
            "new_state": target_state,
            "trigger": trigger,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
    await db.flush()


async def evaluate_rider_eligibility_and_scores(
    db: AsyncSession,
    order: Order,
    store: Store,
    is_batch: bool
) -> List[Tuple[Rider, float]]:
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Rider).where(Rider.status.in_(["IDLE", "BATCHING", "RETURNING"]))
    )
    all_active_riders = result.scalars().all()

    eligible_scored_candidates = []

    for rider in all_active_riders:
        if not rider.is_available:
            logger.warning(f"Rejected rider {rider.id}: reason=RIDER_NOT_AVAILABLE")
            continue

        if rider.battery_level < 15.0:
            logger.warning(f"Rejected rider {rider.id}: reason=BATTERY_LOW_VAL ({rider.battery_level}%)")
            continue

        shift_end = rider.shift_end_time.replace(tzinfo=timezone.utc) if rider.shift_end_time.tzinfo is None else rider.shift_end_time
        if shift_end <= now:
            logger.warning(f"Rejected rider {rider.id}: reason=SHIFT_EXPIRED (ended at {shift_end.isoformat()})")
            continue

        heartbeat_time = rider.last_heartbeat_at.replace(tzinfo=timezone.utc) if rider.last_heartbeat_at.tzinfo is None else rider.last_heartbeat_at
        heartbeat_age_sec = (now - heartbeat_time).total_seconds()
        # if heartbeat_age_sec > 30.0:
        #     logger.warning(f"Rejected rider {rider.id}: reason=HEARTBEAT_LOST (last updated {heartbeat_age_sec}s ago)")
        #     continue
        # For testing purpose adding heartbeat checking from 30 sec to 6hrs
    
        if heartbeat_age_sec > 36000.0:
            logger.warning(f"Rejected rider {rider.id}: reason=HEARTBEAT_LOST")
            continue

        load = await repository.get_rider_active_load_count(db, rider.id)
        if load >= 3:
            logger.warning(f"Rejected rider {rider.id}: reason=MAX_LOAD_REACHED (carrying {load} orders)")
            continue

        score = calculate_rae_score(rider, order, store, load, is_batch_compatible=is_batch)

        logger.info(
            f"Evaluating rider={rider.id}, "
            f"available={rider.is_available}, "
            f"status={rider.status}, "
            f"battery={rider.battery_level}, "
            f"load={load}, "
            f"score={score}"
        )

        if score < 0.55:
            logger.warning(f"Rejected rider {rider.id}: reason=RAE_SCORE_BELOW_THRESHOLD (score {score} < 0.55)")
            continue

        eligible_scored_candidates.append((rider, score))

    return eligible_scored_candidates


async def ingest_new_order(db: AsyncSession, order_id: int) -> Dict[str, Any]:
    """
    Ingests placed orders into the dispatch geofencing and batching pipelines [1].
    Consolidates SLA/Zone logic by reading pre-calculated fields directly from the Order [1].
    """
    order = await repository.get_order_for_update(db, order_id)
    if not order:
        raise ResourceNotFoundException("Order not found")

    if order.status in ["CANCELLED", "COMPLETED"]:
        raise IMSException(f"Cannot dispatch order in status {order.status}", 400)
        
    if order.assignment_status in ["ASSIGNED", "OFFERED", "DELIVERING"]:
        raise IMSException(f"Order is already assigned or offered", 400)

    # 1. Evaluate pre-calculated zone status
    # Zone D is strictly barred from batching
    if order.delivery_zone == "ZONE_D":
        store = await repository.get_store_by_id(db, order.store_id)
        if not store:
            raise IMSException("Origin Dark Store not found", 404)
        return await find_and_offer_solo_rider(db, order, store, is_batch=False)

    # 2. Community Geofence Check
    community = await repository.resolve_location_to_community(db, order.latitude, order.longitude)
    if community:
        order.community_id = community.id
        await db.flush()

        batch_window_sec = await get_dynamic_batch_window(db, community.id)
        batch = await repository.get_active_batch_for_community(db, community.id)

        if not batch:
            dispatch_time = datetime.now(timezone.utc) + timedelta(seconds=batch_window_sec)
            batch = await repository.create_batch(db, community.id, dispatch_time)

        order.batch_id = batch.id
        await db.flush()

        # 3. Eagerly reload batch orders to verify size limits [1]
        batch_hydrated = await repository.get_batch_by_id_with_orders(db, batch.id)
        if not batch_hydrated:
            raise ResourceNotFoundException("Batch not found after assignment")

        if len(batch_hydrated.orders) >= community.max_batch_size:
            store = await repository.get_store_by_id(db, order.store_id)
            if not store:
                raise IMSException("Origin Dark Store not found", 404)
            return await trigger_batch_assignment(db, batch_hydrated, store, community)

        return {
            "order_id": order.id,
            "status": "BATCH_BUFFERED",
            "message": f"Buffered in draft batch {batch_hydrated.id} (dynamic window: {batch_window_sec}s)"
        }

    # 4. Fallback if no geofenced communities match
    store = await repository.get_store_by_id(db, order.store_id)
    if not store:
        raise IMSException("Origin Dark Store not found", 404)
    return await find_and_offer_solo_rider(db, order, store, is_batch=False)


async def find_and_offer_solo_rider(db: AsyncSession, order: Order, store: Store, is_batch: bool) -> Dict[str, Any]:
    candidates = await evaluate_rider_eligibility_and_scores(db, order, store, is_batch)

    if not candidates:
        order.assignment_status = "QUEUED"
        await db.flush()
        return {"order_id": order.id, "status": "NO_RIDER_AVAILABLE", "message": "Queueing order (no rider passed eligibility or RAE threshold)"}

    best_rider, best_score = max(candidates, key=lambda c: c[1])

    order.offered_rider_id = best_rider.id
    order.assignment_offered_at = datetime.now(timezone.utc)
    order.assignment_status = "OFFERED"
    await db.flush()

    return {
        "order_id": order.id,
        "offered_rider_id": best_rider.id,
        "rae_score": best_score,
        "status": "OFFERED"
    }


async def trigger_batch_assignment(db: AsyncSession, batch: Batch, store: Store, community: Community) -> Dict[str, Any]:
    if not batch.orders:
        raise IMSException("Cannot assign empty batch", 400)

    proxy_order = batch.orders[0]
    candidates = await evaluate_rider_eligibility_and_scores(db, proxy_order, store, is_batch=True)

    if not candidates:
        batch.dispatch_by = datetime.now(timezone.utc) + timedelta(seconds=30)
        await db.flush()
        return {"batch_id": batch.id, "status": "QUEUED_NO_RIDER"}

    best_rider, best_score = max(candidates, key=lambda c: c[1])

    # actual batch size at dispatch time 
    batch.actual_batch_size = len(batch.orders)

    batch.offered_rider_id = best_rider.id
    batch.assignment_offered_at = datetime.now(timezone.utc)
    batch.status = "OFFERED"
    await db.flush()

    return {
        "batch_id": batch.id,
        "offered_rider_id": best_rider.id,
        "rae_score": best_score,
        "status": "OFFERED"
    }


async def get_dynamic_batch_window(db: AsyncSession, community_id: str) -> int:
    order_rate = await repository.get_hourly_order_rate_for_community(db, community_id)
    if order_rate < 2:
        return 45
    elif order_rate < 5:
        return 90
    elif order_rate <= 10:
        return 120
    else:
        return 60


async def respond_to_assignment(
    db: AsyncSession,
    rider_id: int,
    order_id: int | None,
    batch_id: int | None,
    accepted: bool
):
    rider = await db.get(Rider, rider_id)
    if not rider:
        raise ResourceNotFoundException("Rider not found")

    if accepted:
        rider.consecutive_declines = 0
        await update_rider_state(db, rider, "ASSIGNED", trigger="ACCEPT_ASSIGNMENT")

        if batch_id:
            batch = await repository.get_batch_by_id_for_update(db, batch_id)
            if not batch:
                raise ResourceNotFoundException("Batch not found")

            batch.rider_id = rider.id
            batch.offered_rider_id = None
            batch.assignment_offered_at = None
            batch.status = "ASSIGNED"

            if not batch.orders:
                raise IMSException("Cannot process batch with no orders", 400)

            store = await repository.get_store_by_id(db, batch.orders[0].store_id)
            if not store:
                raise ResourceNotFoundException("Origin Store not found")

            community = await db.get(Community, batch.community_id)
            if not community:
                raise ResourceNotFoundException("Community geofence not found")

            orders_data = [{"id": o.id, "latitude": o.latitude, "longitude": o.longitude} for o in batch.orders]
            gate = community.entry_points[0]

            # TSP Drop Routing 
            optimized = optimize_drops(orders_data, (gate["lat"], gate["lon"]))
            for index, seq in enumerate(optimized):
                ord_item = next(o for o in batch.orders if o.id == seq["id"])
                ord_item.rider_id = rider.id
                ord_item.assignment_status = "ASSIGNED"

            await db.commit()
            return {"status": "BATCH_ACCEPTED", "sequence": [o["id"] for o in optimized]}

        elif order_id:
            order = await repository.get_order_for_update(db, order_id)
            if not order:
                raise ResourceNotFoundException("Order not found")

            order.rider_id = rider.id
            order.offered_rider_id = None
            order.assignment_offered_at = None
            order.assignment_status = "ASSIGNED"
            await db.commit()
            return {"status": "ORDER_ACCEPTED", "order_id": order.id}

    else:
        rider.consecutive_declines += 1

        # Mandatory assignment on 3rd consecutive decline
        if rider.consecutive_declines >= 3:
            logger.warning(
                f"MANDATORY_ASSIGNMENT: rider {rider.id} has {rider.consecutive_declines} consecutive declines. "
                f"Force-assigning and flagging for ops review."
            )
            rider.mandatory_assignment_flag = True

            await repository.create_outbox_event(
                db,
                "dispatch.mandatory_assignment",
                {
                    "rider_id": rider.id,
                    "consecutive_declines": rider.consecutive_declines,
                    "order_id": order_id,
                    "batch_id": batch_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

            # Force-assign the order/batch directly, bypassing normal accept flow
            if order_id:
                order = await repository.get_order_for_update(db, order_id)
                if order:
                    order.rider_id = rider.id
                    order.offered_rider_id = None
                    order.assignment_offered_at = None
                    order.assignment_status = "ASSIGNED"
                    rider.is_available = False
                    rider.status = "ASSIGNED"
                    rider.consecutive_declines = 0
                    await db.commit()
                    return {"status": "MANDATORY_ASSIGNED", "order_id": order.id, "rider_id": rider.id}

            elif batch_id:
                batch = await repository.get_batch_by_id_for_update(db, batch_id)
                if batch:
                    batch.rider_id = rider.id
                    batch.offered_rider_id = None
                    batch.assignment_offered_at = None
                    batch.status = "ASSIGNED"
                    for o in batch.orders:
                        o.rider_id = rider.id
                        o.assignment_status = "ASSIGNED"
                    rider.is_available = False
                    rider.status = "ASSIGNED"
                    rider.consecutive_declines = 0
                    await db.commit()
                    return {"status": "MANDATORY_ASSIGNED_BATCH", "batch_id": batch.id, "rider_id": rider.id}

        # Performance penalty threshold 
        if rider.consecutive_declines >= 2:
            rider.performance_score = max(0.4, rider.performance_score - 0.1)

        await update_rider_state(db, rider, "IDLE", trigger="DECLINE_ASSIGNMENT")

        if order_id:
            order = await repository.get_order_for_update(db, order_id)
            if not order:
                raise ResourceNotFoundException("Order not found")

            order.offered_rider_id = None
            order.assignment_offered_at = None
            order.assignment_status = "UNASSIGNED"
            await db.commit()

        elif batch_id:
            batch = await repository.get_batch_by_id_for_update(db, batch_id)
            if not batch:
                raise ResourceNotFoundException("Batch not found")

            batch.offered_rider_id = None
            batch.assignment_offered_at = None
            batch.status = "DRAFT"
            await db.commit()

        return {"status": "DECLINED_REGISTERED"}


async def record_heartbeat(db: AsyncSession, rider_id: int, lat: float, lon: float, battery: float):
    rider = await db.get(Rider, rider_id)
    if not rider:
        raise ResourceNotFoundException("Rider not found")

    rider.latitude = lat
    rider.longitude = lon
    rider.battery_level = battery
    rider.last_heartbeat_at = datetime.now(timezone.utc)

    if rider.status == "OFFLINE":
        await update_rider_state(db, rider, "IDLE", trigger="HEARTBEAT_RECOVERED")

    await db.commit()


async def get_all_active_batches(db: AsyncSession) -> List[Batch]:
    return await repository.get_all_active_batches(db)


async def get_batch_details(db: AsyncSession, batch_id: int) -> Batch:
    batch = await repository.get_batch_by_id_with_orders(db, batch_id)
    if not batch:
        raise ResourceNotFoundException("Batch not found")
    return batch


async def execute_manual_sweep(db: AsyncSession):
    # Local import inside the function breaks the module-load circular import loop
    from app.modules.dispatch.tasks import run_dispatch_sweep_cycle
    await run_dispatch_sweep_cycle(db)



async def record_dispatch_latency(db: AsyncSession, path: str, duration_ms: float) -> None:
    """Records a latency sample for percentile analysis."""
    await repository.record_latency_sample(db, path, duration_ms)