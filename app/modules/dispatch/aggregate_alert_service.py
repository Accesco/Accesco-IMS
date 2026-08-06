# app/modules/dispatch/aggregate_alert_service.py
"""
Rolling aggregate alerts for on-time delivery rate and re-assignment rate.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.modules.dispatch import repository

logger = logging.getLogger("aggregate_alert_service")


ON_TIME_RATE_THRESHOLD = 0.88      
REASSIGNMENT_RATE_THRESHOLD = 0.06  
ON_TIME_WINDOW_MINUTES = 10
REASSIGNMENT_WINDOW_MINUTES = 15


class AggregateAlertService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_aggregate_checks(self) -> None:
        """Entry point called from the sweep cycle """
        await self.check_on_time_delivery_rate()
        await self.check_reassignment_rate()

    async def check_on_time_delivery_rate(self) -> float:
        """
        Checks whether on-time delivery rate dropped below 88% in the last
        10-minute rolling window.  Emits "sla.aggregate_breach" if so.
        Returns the computed rate (0.0–1.0) for test introspection.
        """
        now = datetime.now(timezone.utc)
        since = now - timedelta(minutes=ON_TIME_WINDOW_MINUTES)

        # Count delivered orders in the window
        delivered_res = await self.db.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.status == "DELIVERED",
                    Order.actual_delivered_at >= since,
                )
            )
        )
        delivered_total = int(delivered_res.scalar() or 0)

        if delivered_total == 0:
            return 1.0  # No data — do not alert

        # Count on-time deliveries (delivered before or at SLA deadline)
        on_time_res = await self.db.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.status == "DELIVERED",
                    Order.actual_delivered_at >= since,
                    Order.actual_delivered_at <= Order.sla_deadline,
                )
            )
        )
        on_time_count = int(on_time_res.scalar() or 0)

        rate = on_time_count / delivered_total

        if rate < ON_TIME_RATE_THRESHOLD:
            logger.error(
                f"AGGREGATE_SLA_BREACH: on_time_rate={rate:.2%} < threshold={ON_TIME_RATE_THRESHOLD:.0%} "
                f"over last {ON_TIME_WINDOW_MINUTES}min"
            )
            await repository.create_outbox_event(
                self.db,
                "sla.aggregate_breach",
                {
                    "on_time_rate": round(rate, 4),
                    "threshold": ON_TIME_RATE_THRESHOLD,
                    "window_minutes": ON_TIME_WINDOW_MINUTES,
                    "delivered_total": delivered_total,
                    "on_time_count": on_time_count,
                    "timestamp": now.isoformat(),
                },
            )

        return rate

    async def check_reassignment_rate(self) -> float:
        """
        Checks whether re-assignment rate exceeded 6% in the last 15-minute window.
        Emits "dispatch.high_reassignment_rate" if so.
        Returns computed rate for test introspection.
        """
        now = datetime.now(timezone.utc)
        since = now - timedelta(minutes=REASSIGNMENT_WINDOW_MINUTES)

        # Total orders touched (offered or assigned) in the window
        total_res = await self.db.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.assignment_offered_at >= since,
                )
            )
        )
        total = int(total_res.scalar() or 0)

        if total == 0:
            return 0.0

        # Reassigned = orders that were OFFERED and then returned to UNASSIGNED
        # Proxy: orders currently UNASSIGNED but had an offer (offered_rider_id cleared)
        # More accurate: count outbox events of type OFFER_TIMEOUT / DECLINE in window.
        # For the rule-based stand-in, we use: UNASSIGNED orders with no current offered_rider_id
        reassigned_res = await self.db.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.assignment_status == "UNASSIGNED",
                    Order.assignment_offered_at >= since,
                    Order.offered_rider_id.is_(None),
                )
            )
        )
        reassigned_count = int(reassigned_res.scalar() or 0)

        rate = reassigned_count / total if total > 0 else 0.0

        if rate > REASSIGNMENT_RATE_THRESHOLD:
            logger.error(
                f"HIGH_REASSIGNMENT_RATE: rate={rate:.2%} > threshold={REASSIGNMENT_RATE_THRESHOLD:.0%} "
                f"over last {REASSIGNMENT_WINDOW_MINUTES}min"
            )
            await repository.create_outbox_event(
                self.db,
                "dispatch.high_reassignment_rate",
                {
                    "reassignment_rate": round(rate, 4),
                    "threshold": REASSIGNMENT_RATE_THRESHOLD,
                    "window_minutes": REASSIGNMENT_WINDOW_MINUTES,
                    "total_offers": total,
                    "reassigned_count": reassigned_count,
                    "timestamp": now.isoformat(),
                },
            )

        return rate
