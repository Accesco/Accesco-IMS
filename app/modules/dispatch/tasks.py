# app/modules/dispatch/tasks.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch
from app.models.order import Order
from app.models.rider import Rider
from app.models.community import Community


async def run_dispatch_sweep_cycle(db: AsyncSession):
    """
    Autonomous sweeping task that monitors background dispatcher timeouts,
    expired offers, and offline state transitions (Section 11) [14.1].
    """
    now = datetime.now(timezone.utc)

    # 1. Release Wait Windows and SLA Breech Risks (Eagerly loading orders) [1]
    batches_result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.orders)) # Eager load orders to prevent MissingGreenlet [1]
        .where(Batch.status == "DRAFT")
    )
    draft_batches = batches_result.scalars().all()
    
    for batch in draft_batches:
        if not batch.orders:
            continue
            
        store = await repository_get_store_by_id(db, batch.orders[0].store_id)
        if not store:
            continue
            
        community = await db.get(Community, batch.community_id)
        if not community:
            continue
        
        # Immediate dispatch on SLA risk (current_time + ETA > deadline - 2 mins) [14.1]
        is_sla_risk = any(
            (o.sla_deadline - timedelta(minutes=2)) < (now + timedelta(minutes=5)) 
            for o in batch.orders
        )
        
        # Local helper reference to trigger dispatch directly
        from app.modules.dispatch.service import trigger_batch_assignment
        if now >= batch.dispatch_by or is_sla_risk:
            await trigger_batch_assignment(db, batch, store, community)

    # 2. Timeout 45-Second Offers (Section 11)
    timeout_threshold = now - timedelta(seconds=45)
    
    # Solo Orders Timeouts
    expired_orders_res = await db.execute(
        select(Order).where(
            and_(
                Order.assignment_status == "OFFERED",
                Order.assignment_offered_at <= timeout_threshold
            )
        )
    )
    for order in expired_orders_res.scalars().all():
        rider = await db.get(Rider, order.offered_rider_id)
        if rider:
            rider.consecutive_declines += 1
            # Import inline to prevent circular import loops during tasks load [1.1.6]
            from app.modules.dispatch.service import update_rider_state
            await update_rider_state(db, rider, "IDLE", trigger="OFFER_TIMEOUT")
        
        order.offered_rider_id = None
        order.assignment_offered_at = None
        order.assignment_status = "UNASSIGNED"
        await db.commit()

    # Batch Timeouts
    expired_batches_res = await db.execute(
        select(Batch).where(
            and_(
                Batch.status == "OFFERED",
                Batch.assignment_offered_at <= timeout_threshold
            )
        )
    )
    for batch in expired_batches_res.scalars().all():
        rider = await db.get(Rider, batch.offered_rider_id)
        if rider:
            rider.consecutive_declines += 1
            from app.modules.dispatch.service import update_rider_state
            await update_rider_state(db, rider, "IDLE", trigger="BATCH_OFFER_TIMEOUT")
        
        batch.offered_rider_id = None
        batch.assignment_offered_at = None
        batch.status = "DRAFT"
        await db.commit()

    # 3. Mark Idle/Offline status for Connection Losses (Section 11)
    offline_threshold = now - timedelta(seconds=30)
    offline_riders_res = await db.execute(
        select(Rider).where(
            and_(
                Rider.status != "OFFLINE",
                Rider.last_heartbeat_at < offline_threshold
            )
        )
    )
    for offline_rider in offline_riders_res.scalars().all():
        from app.modules.dispatch.service import update_rider_state
        await update_rider_state(db, offline_rider, "OFFLINE", trigger="HEARTBEAT_LOST")
        
        active_orders_res = await db.execute(
            select(Order).where(
                and_(
                    Order.rider_id == offline_rider.id,
                    Order.status.in_(["PENDING", "ACCEPTED"])
                )
            )
        )
        for order in active_orders_res.scalars().all():
            order.rider_id = None
            order.assignment_status = "UNASSIGNED"
            await db.commit()
            
            store = await repository_get_store_by_id(db, order.store_id)
            if store:
                from app.modules.dispatch.service import find_and_offer_solo_rider
                await find_and_offer_solo_rider(db, order, store, is_batch=False)


# Helper function local lookup
async def repository_get_store_by_id(db: AsyncSession, store_id: int):
    from app.models.store import Store
    res = await db.execute(select(Store).where(Store.id == store_id))
    return res.scalar_one_or_none()