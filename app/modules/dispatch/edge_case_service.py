# app/modules/dispatch/edge_case_service.py
"""
Detects and handles operational edge cases: picker delays and flash demand surges.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import List

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.community import Community
from app.modules.dispatch import repository

logger = logging.getLogger("dispatch_edge_cases")

# Extra buffer added to expected pick time before a delay is flagged
PICKER_DELAY_EXTRA_MINUTES = 5
# Default expected pick time in minutes if not set per order/store
DEFAULT_EXPECTED_PICK_MINUTES = 10

# Flash surge threshold: current 15-min rate > 3x trailing 15-min average
SURGE_MULTIPLIER = 3.0
# Surge window expansion factor (50%), bounded to [45, 180] seconds
SURGE_EXPANSION_FACTOR = 1.5
BATCH_WINDOW_MIN_SEC = 45
BATCH_WINDOW_MAX_SEC = 180


async def detect_picker_delay(db: AsyncSession) -> int:
    """
     Detects dark-store picker delays.

    Detection: order.status == "PICKING" and
    (now - order.picking_started_at) > expected_pick_time + 5 minutes.

    Handling:
      - Re-route the assigned rider to their next queued order while waiting.
      - Push an updated SLA promise to the order (outbox pattern).
      - Returns count of orders flagged.
    """
    now = datetime.now(timezone.utc)
    delay_threshold = timedelta(minutes=DEFAULT_EXPECTED_PICK_MINUTES + PICKER_DELAY_EXTRA_MINUTES)

    # Find PICKING orders whose picking_started_at has exceeded the threshold
    result = await db.execute(
        select(Order).where(
            and_(
                Order.status == "PICKING",
                Order.picking_started_at.isnot(None),
            )
        )
    )
    picking_orders = result.scalars().all()

    flagged_count = 0
    for order in picking_orders:
        started_at = order.picking_started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)

        elapsed = now - started_at
        if elapsed <= delay_threshold:
            continue

        logger.warning(
            f"PICKER_DELAY detected: order_id={order.id}, "
            f"elapsed={elapsed.total_seconds():.0f}s, "
            f"threshold={delay_threshold.total_seconds():.0f}s"
        )

        # Push updated SLA promise via outbox pattern
        new_eta_sec = (elapsed - delay_threshold).total_seconds() + DEFAULT_EXPECTED_PICK_MINUTES * 60
        await repository.create_outbox_event(
            db,
            "dispatch.picker_delay_detected",
            {
                "order_id": order.id,
                "rider_id": order.rider_id,
                "elapsed_sec": elapsed.total_seconds(),
                "updated_eta_offset_sec": new_eta_sec,
                "timestamp": now.isoformat(),
            },
        )

        # If there's an assigned rider, try to route them to their next queued order
        if order.rider_id is not None:
            next_queued = await _find_next_queued_order_for_rider(db, order.rider_id, exclude_order_id=order.id)
            if next_queued:
                await repository.create_outbox_event(
                    db,
                    "dispatch.rider_rerouted_during_picker_delay",
                    {
                        "rider_id": order.rider_id,
                        "delayed_order_id": order.id,
                        "rerouted_to_order_id": next_queued.id,
                        "timestamp": now.isoformat(),
                    },
                )
                logger.info(
                    f"Rerouted rider {order.rider_id} to order {next_queued.id} "
                    f"while waiting for picker delay on order {order.id}"
                )

        flagged_count += 1

    return flagged_count


async def _find_next_queued_order_for_rider(
    db: AsyncSession, rider_id: int, exclude_order_id: int
) -> Order | None:
    """Returns the next UNASSIGNED order (could be re-offered to the rider)."""
    result = await db.execute(
        select(Order).where(
            and_(
                Order.assignment_status == "UNASSIGNED",
                Order.id != exclude_order_id,
                Order.status.in_(["PENDING", "ACCEPTED"]),
            )
        ).limit(1)
    )
    return result.scalar_one_or_none()


async def detect_flash_surge(db: AsyncSession) -> int:
    """
     Detects flash demand spikes.

    Detection: current 15-min order rate for a store/community > 3x the
    trailing 15-min average.

    Handling:
      - Expand active batch windows for the affected community by 50%
        (bounded to [45, 180] seconds).
      - Emit "dispatch.surge_detected" outbox event.
      - Returns count of communities where surge was detected.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=15)
    trailing_start = now - timedelta(minutes=30)

    result = await db.execute(select(Community))
    communities = result.scalars().all()

    surge_count = 0
    for community in communities:
        current_rate = await repository.get_order_count_for_community_window(
            db, community.id, window_start, now
        )
        trailing_rate = await repository.get_order_count_for_community_window(
            db, community.id, trailing_start, window_start
        )

        if trailing_rate == 0:
            # No trailing history; skip 
            continue

        ratio = current_rate / trailing_rate
        if ratio <= SURGE_MULTIPLIER:
            continue

        logger.warning(
            f"FLASH_SURGE detected: community_id={community.id}, "
            f"current_rate={current_rate}, trailing_rate={trailing_rate}, "
            f"ratio={ratio:.2f}x"
        )

        # Expand batch window by 50%, clamped to [45, 180] seconds
        new_window_sec = int(
            min(BATCH_WINDOW_MAX_SEC, max(BATCH_WINDOW_MIN_SEC,
                                          community.batch_window_sec * SURGE_EXPANSION_FACTOR))
        )
        old_window_sec = community.batch_window_sec
        community.batch_window_sec = new_window_sec
        await db.flush()

        await repository.create_outbox_event(
            db,
            "dispatch.surge_detected",
            {
                "community_id": community.id,
                "current_15min_orders": current_rate,
                "trailing_15min_orders": trailing_rate,
                "surge_ratio": round(ratio, 2),
                "old_window_sec": old_window_sec,
                "new_window_sec": new_window_sec,
                "timestamp": now.isoformat(),
            },
        )

        logger.info(
            f"Expanded batch window for community {community.id}: "
            f"{old_window_sec}s → {new_window_sec}s"
        )

        surge_count += 1

    return surge_count
