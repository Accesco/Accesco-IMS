
from __future__ import annotations

import logging
import traceback
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch
from app.models.order import Order
from app.models.rider import Rider
from app.models.community import Community

logger = logging.getLogger("dispatch_sweep")
logger.setLevel(logging.INFO)


async def run_dispatch_sweep_cycle(db: AsyncSession):
    """
    Autonomous sweeping task that monitors background dispatcher timeouts,
    expired offers, and offline state transitions.
    """
    now = datetime.now(timezone.utc)

    # 1. Release Wait Windows and SLA Breach Risks
    batches_result = await db.execute(
        select(Batch)
        .options(selectinload(Batch.orders))
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

        is_sla_risk = any(
            (o.sla_deadline.replace(tzinfo=timezone.utc) - timedelta(minutes=2)) < (now + timedelta(minutes=5))
            if o.sla_deadline.tzinfo is None else (o.sla_deadline - timedelta(minutes=2)) < (now + timedelta(minutes=5))
            for o in batch.orders
        )

        from app.modules.dispatch.service import trigger_batch_assignment
        if now >= batch.dispatch_by.replace(tzinfo=timezone.utc) or is_sla_risk:
            await trigger_batch_assignment(db, batch, store, community)

    # 2. Timeout 45-Second Offers 
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

    # 3. Mark Idle/Offline status for Connection Losses
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

    # 4. Trigger the Global Hungarian Optimization Loop 
    try:
        from app.modules.dispatch.optimizer_service import GlobalDispatchOptimizer
        from app.core.database import get_redis_client
        redis_client = get_redis_client()
        optimizer = GlobalDispatchOptimizer(db, redis_client)
        await optimizer.execute_global_optimization_sweep()
    except Exception as exc:
        _handle_sweep_component_failure(db, "optimizer_sweep", exc)

    # 5. Run SLA Alerting Monitors 
    try:
        from app.modules.dispatch.sla_monitor_service import SLAMonitorService
        sla_monitor = SLAMonitorService(db)
        await sla_monitor.run_sla_breach_detection_sweep()
    except Exception as exc:
        _handle_sweep_component_failure(db, "sla_monitor", exc)

    # 6. 
    try:
        from app.modules.dispatch.edge_case_service import detect_picker_delay, detect_flash_surge
        await detect_picker_delay(db)
        await detect_flash_surge(db)
    except Exception as exc:
        _handle_sweep_component_failure(db, "edge_case_detection", exc)

    # 7.  aggregate-level SLA and re-assignment alerts 
    try:
        from app.modules.dispatch.aggregate_alert_service import AggregateAlertService
        agg_svc = AggregateAlertService(db)
        await agg_svc.run_aggregate_checks()
    except Exception as exc:
        _handle_sweep_component_failure(db, "aggregate_alert_service", exc)


def _handle_sweep_component_failure(db: AsyncSession, component: str, exc: Exception) -> None:
    """
    Centralized failure handler for sweep sub-components.
    """
    logger.error(
        f"SWEEP_COMPONENT_FAILED component={component} error={exc!r}\n"
        f"{traceback.format_exc()}"
    )

    import asyncio

    async def _emit():
        try:
            from app.modules.dispatch.repository import create_outbox_event
            await create_outbox_event(
                db,
                "dispatch.sweep_component_failed",
                {
                    "component": component,
                    "error": repr(exc),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            await db.flush()
        except Exception as inner:
            logger.error(f"Could not write outbox event for failed component {component}: {inner!r}")

    # Schedule the coroutine on the running loop if possible
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_emit())
    except RuntimeError:
        pass  


async def repository_get_store_by_id(db: AsyncSession, store_id: int):
    from app.models.store import Store
    res = await db.execute(select(Store).where(Store.id == store_id))
    return res.scalar_one_or_none()