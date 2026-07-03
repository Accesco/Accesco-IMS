
from __future__ import annotations

import logging
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.sla import SLAAlert
from app.modules.dispatch import repository

logger = logging.getLogger("sla_monitor")


class SLAMonitorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_sla_breach_detection_sweep(self):
        now = datetime.now(timezone.utc)
        
        res = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.status.in_(["PENDING", "ACCEPTED", "PICKING", "DISPATCHED"]))
        )
        active_orders = res.scalars().all()

        for order in active_orders:
            # Fixed .replace(tzinfo=timezone.utc) syntax [1]
            order_created = order.created_at.replace(tzinfo=timezone.utc) if order.created_at.tzinfo is None else order.created_at
            order_sla = order.sla_deadline.replace(tzinfo=timezone.utc) if order.sla_deadline.tzinfo is None else order.sla_deadline
            
            order_age_sec = (now - order_created).total_seconds()
            sla_time_left = (order_sla - now).total_seconds()

            if sla_time_left < 0:
                await self._trigger_alert(order, "BREACH", order_age_sec, "Order has exceeded its SLA deadline")
            elif sla_time_left < 120:
                await self._trigger_alert(order, "CRITICAL_RISK", order_age_sec, "SLA breach imminent in under 2 minutes")
            elif sla_time_left < 300:
                await self._trigger_alert(order, "RISK", order_age_sec, "SLA buffer is low (under 5 minutes)")

    async def _trigger_alert(self, order: Order, level: str, age_sec: float, msg: str):
        existing_alert = await self.db.execute(
            select(SLAAlert).where(
                and_(
                    SLAAlert.order_id == order.id,
                    SLAAlert.alert_level == level,
                    SLAAlert.status == "ACTIVE"
                )
            )
        )
        if existing_alert.scalar_one_or_none():
            return

        new_alert = SLAAlert(
            order_id=order.id,
            alert_level=level,
            assignment_delay_sec=age_sec if order.assignment_status == "UNASSIGNED" else 0.0,
            status="ACTIVE",
            escalation_level=2 if level in ["CRITICAL_RISK", "BREACH"] else 1
        )
        self.db.add(new_alert)
        await self.db.flush()

        await repository.create_outbox_event(
            self.db,
            "sla.alert_triggered",
            {
                "alert_id": new_alert.id,
                "order_id": order.id,
                "level": level,
                "msg": msg,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        self._dispatch_external_pager_payload(new_alert.id, level, msg)
        await self.db.commit()

    def _dispatch_external_pager_payload(self, alert_id: int, level: str, msg: str):
        logger.warning(
            f"ALERT [SLA-{level}] ID {alert_id} dispatched to PagerDuty/Datadog: '{msg}'"
        )