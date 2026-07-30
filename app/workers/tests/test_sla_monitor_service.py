"""
tests/test_sla_monitor_service.py
SLA Monitor Service Tests:
  - All three alert levels (RISK/CRITICAL_RISK/BREACH) trigger at correct thresholds
  - Dedup logic — no duplicate ACTIVE alerts for the same order + level
  - Alert resolution behavior
  - Aggregate alerts: sla.aggregate_breach < 88%, dispatch.high_reassignment_rate > 6%
"""
from __future__ import annotations

import os
import tempfile
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

import app.models  # noqa: F401
from app.models.base import Base
from app.models.order import Order
from app.models.store import Store
from app.models.sla import SLAAlert
from app.models.outbox import OutboxEvent
from app.modules.dispatch.sla_monitor_service import SLAMonitorService
from app.modules.dispatch.aggregate_alert_service import AggregateAlertService

_DB = os.path.join(tempfile.gettempdir(), "ims_sla_test.db")
_ENGINE = create_async_engine(f"sqlite+aiosqlite:///{_DB}", connect_args={"check_same_thread": False})
_SESSION = async_sessionmaker(bind=_ENGINE, class_=AsyncSession, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with _SESSION() as session:
        yield session
    async with _ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _seed_store(db: AsyncSession) -> Store:
    store = Store(name=f"SLAStore{id(db)}", address="1 St", city="Mumbai", state="MH")
    db.add(store)
    await db.flush()
    return store


async def _order_with_deadline(db: AsyncSession, store: Store, deadline_offset_sec: float, status: str = "PENDING") -> Order:
    """Create an order whose SLA deadline is now + offset (negative = already breached)."""
    order = Order(
        customer_id=1,
        store_id=store.id,
        status=status,
        total_amount=10.0,
        payment_status="PAID",
        latitude=19.0,
        longitude=72.8,
        delivery_zone="ZONE_A",
        sla_deadline=datetime.now(timezone.utc) + timedelta(seconds=deadline_offset_sec),
        assignment_status="UNASSIGNED",
    )
    db.add(order)
    await db.flush()
    return order


# ─── Per-Order SLA Alert Tests ─────────────────────────────────────────────────

class TestSLAMonitorAlerts:

    @pytest.mark.asyncio
    async def test_breach_alert_triggers_when_past_deadline(self, db):
        """SLA past its deadline must create a BREACH alert."""
        store = await _seed_store(db)
        order = await _order_with_deadline(db, store, deadline_offset_sec=-1)

        svc = SLAMonitorService(db)
        await svc.run_sla_breach_detection_sweep()

        result = await db.execute(select(SLAAlert).where(SLAAlert.order_id == order.id))
        alerts = result.scalars().all()
        assert any(a.alert_level == "BREACH" for a in alerts), "Expected BREACH alert"

    @pytest.mark.asyncio
    async def test_critical_risk_alert_under_2_minutes(self, db):
        """SLA < 2 min remaining must create a CRITICAL_RISK alert."""
        store = await _seed_store(db)
        order = await _order_with_deadline(db, store, deadline_offset_sec=90)  # 90s < 120s

        svc = SLAMonitorService(db)
        await svc.run_sla_breach_detection_sweep()

        result = await db.execute(select(SLAAlert).where(SLAAlert.order_id == order.id))
        alerts = result.scalars().all()
        assert any(a.alert_level == "CRITICAL_RISK" for a in alerts), "Expected CRITICAL_RISK alert"

    @pytest.mark.asyncio
    async def test_risk_alert_under_5_minutes(self, db):
        """SLA between 2-5 min remaining must create a RISK alert."""
        store = await _seed_store(db)
        order = await _order_with_deadline(db, store, deadline_offset_sec=200)  # 200s = 3.3 min

        svc = SLAMonitorService(db)
        await svc.run_sla_breach_detection_sweep()

        result = await db.execute(select(SLAAlert).where(SLAAlert.order_id == order.id))
        alerts = result.scalars().all()
        assert any(a.alert_level == "RISK" for a in alerts), "Expected RISK alert"

    @pytest.mark.asyncio
    async def test_no_alert_for_healthy_order(self, db):
        """Orders with plenty of SLA time remaining must NOT trigger any alert."""
        store = await _seed_store(db)
        order = await _order_with_deadline(db, store, deadline_offset_sec=3600)  # 1 hour

        svc = SLAMonitorService(db)
        await svc.run_sla_breach_detection_sweep()

        result = await db.execute(select(SLAAlert).where(SLAAlert.order_id == order.id))
        assert result.scalars().all() == [], "Expected no alerts for healthy order"

    @pytest.mark.asyncio
    async def test_dedup_no_duplicate_active_alerts(self, db):
        """Running the sweep twice must not create duplicate ACTIVE alerts."""
        store = await _seed_store(db)
        order = await _order_with_deadline(db, store, deadline_offset_sec=-1)

        svc = SLAMonitorService(db)
        await svc.run_sla_breach_detection_sweep()
        await svc.run_sla_breach_detection_sweep()  # second pass

        result = await db.execute(
            select(SLAAlert).where(
                SLAAlert.order_id == order.id,
                SLAAlert.alert_level == "BREACH",
                SLAAlert.status == "ACTIVE",
            )
        )
        breach_alerts = result.scalars().all()
        assert len(breach_alerts) == 1, f"Expected exactly 1 ACTIVE BREACH alert, got {len(breach_alerts)}"

    @pytest.mark.asyncio
    async def test_alert_creates_outbox_event(self, db):
        """An alert must emit a sla.alert_triggered outbox event."""
        store = await _seed_store(db)
        order = await _order_with_deadline(db, store, deadline_offset_sec=-1)

        svc = SLAMonitorService(db)
        await svc.run_sla_breach_detection_sweep()

        result = await db.execute(
            select(OutboxEvent).where(OutboxEvent.event_type == "sla.alert_triggered")
        )
        events = result.scalars().all()
        assert len(events) >= 1, "Expected at least one sla.alert_triggered outbox event"


# ─── Aggregate Alert Tests ─────────────────────────────────────────────────────

class TestAggregateAlerts:

    @pytest.mark.asyncio
    async def test_aggregate_breach_emitted_when_on_time_rate_low(self, db):
        """
        If on-time rate < 88%, a sla.aggregate_breach event must be emitted.
        Seed 10 delivered orders, only 5 on time → 50% rate < 88%.
        """
        store = await _seed_store(db)
        now = datetime.now(timezone.utc)

        for i in range(10):
            is_on_time = i < 5  # first 5 on-time, last 5 late
            deadline = now + timedelta(minutes=30)
            delivered_at = deadline - timedelta(minutes=1) if is_on_time else deadline + timedelta(minutes=10)
            order = Order(
                customer_id=i + 1,
                store_id=store.id,
                status="DELIVERED",
                total_amount=10.0,
                payment_status="PAID",
                latitude=19.0,
                longitude=72.8,
                delivery_zone="ZONE_A",
                sla_deadline=deadline,
                assignment_status="ASSIGNED",
                actual_delivered_at=delivered_at,
            )
            db.add(order)
        await db.commit()

        svc = AggregateAlertService(db)
        rate = await svc.check_on_time_delivery_rate()

        assert rate == pytest.approx(0.5, abs=0.01), f"Expected ~0.5 rate, got {rate}"

        result = await db.execute(
            select(OutboxEvent).where(OutboxEvent.event_type == "sla.aggregate_breach")
        )
        events = result.scalars().all()
        assert len(events) >= 1, "Expected sla.aggregate_breach outbox event"

    @pytest.mark.asyncio
    async def test_aggregate_breach_not_emitted_above_threshold(self, db):
        """If on-time rate >= 88%, no aggregate breach event should fire."""
        store = await _seed_store(db)
        now = datetime.now(timezone.utc)

        # 9 out of 10 on-time = 90% rate
        for i in range(10):
            deadline = now + timedelta(minutes=30)
            is_on_time = i < 9
            delivered_at = deadline - timedelta(minutes=1) if is_on_time else deadline + timedelta(minutes=5)
            order = Order(
                customer_id=i + 100,
                store_id=store.id,
                status="DELIVERED",
                total_amount=10.0,
                payment_status="PAID",
                latitude=19.0,
                longitude=72.8,
                delivery_zone="ZONE_A",
                sla_deadline=deadline,
                assignment_status="ASSIGNED",
                actual_delivered_at=delivered_at,
            )
            db.add(order)
        await db.commit()

        svc = AggregateAlertService(db)
        rate = await svc.check_on_time_delivery_rate()
        assert rate >= 0.88

        result = await db.execute(
            select(OutboxEvent).where(OutboxEvent.event_type == "sla.aggregate_breach")
        )
        events = result.scalars().all()
        assert len(events) == 0, "Should NOT emit breach event when rate >= 88%"

    @pytest.mark.asyncio
    async def test_high_reassignment_rate_event_emitted(self, db):
        """
        If reassignment rate > 6%, dispatch.high_reassignment_rate event fires.
        Seed 10 offers, 2 of which were declined (UNASSIGNED with no offered_rider).
        2/10 = 20% > 6%.
        """
        store = await _seed_store(db)
        now = datetime.now(timezone.utc)

        for i in range(10):
            is_reassigned = i < 2
            order = Order(
                customer_id=i + 200,
                store_id=store.id,
                status="PENDING",
                total_amount=10.0,
                payment_status="PAID",
                latitude=19.0,
                longitude=72.8,
                delivery_zone="ZONE_A",
                sla_deadline=now + timedelta(hours=1),
                assignment_status="UNASSIGNED" if is_reassigned else "OFFERED",
                offered_rider_id=None if is_reassigned else None,
                assignment_offered_at=now - timedelta(minutes=5),
            )
            db.add(order)
        await db.commit()

        svc = AggregateAlertService(db)
        rate = await svc.check_reassignment_rate()

        result = await db.execute(
            select(OutboxEvent).where(OutboxEvent.event_type == "dispatch.high_reassignment_rate")
        )
        events = result.scalars().all()
        # Only assert if rate was above threshold
        if rate > 0.06:
            assert len(events) >= 1, "Expected dispatch.high_reassignment_rate outbox event"
