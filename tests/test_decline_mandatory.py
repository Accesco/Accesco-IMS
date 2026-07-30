"""
tests/test_decline_mandatory.py
Mandatory Assignment Tests :
  - Decline #1 → performance penalty not yet applied (only at >=2)
  - Decline #2 → performance score penalty applied
  - Decline #3 → force-assign, mandatory_assignment_flag=True, outbox event emitted
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
from app.models.rider import Rider
from app.models.order import Order
from app.models.store import Store
from app.models.outbox import OutboxEvent
from app.modules.dispatch import service as dispatch_service

_DB = os.path.join(tempfile.gettempdir(), "ims_decline_test.db")
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


async def _seed_rider(db: AsyncSession, phone: str = "9500000001", consecutive_declines: int = 0) -> Rider:
    rider = Rider(
        name="TestRider",
        phone=phone,
        is_available=True,
        status="IDLE",
        battery_level=80.0,
        performance_score=1.0,
        consecutive_declines=consecutive_declines,
        last_heartbeat_at=datetime.now(timezone.utc),
        shift_start_time=datetime.now(timezone.utc),
        shift_end_time=datetime.now(timezone.utc) + timedelta(hours=8),
    )
    db.add(rider)
    await db.flush()
    return rider


async def _seed_order(db: AsyncSession, phone_suffix: str = "001") -> Order:
    store = Store(name=f"DeclineStore{phone_suffix}", address="1 St", city="Mumbai", state="MH")
    db.add(store)
    await db.flush()

    order = Order(
        customer_id=1,
        store_id=store.id,
        status="PENDING",
        total_amount=50.0,
        payment_status="PAID",
        latitude=19.0,
        longitude=72.8,
        delivery_zone="ZONE_A",
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=1),
        assignment_status="OFFERED",
    )
    db.add(order)
    await db.commit()
    return order


class TestDeclineMandatoryAssignment:

    @pytest.mark.asyncio
    async def test_decline_1_increments_counter_no_penalty(self, db):
        """
        First decline: consecutive_declines goes to 1, performance score unchanged.
        """
        rider = await _seed_rider(db, phone="9500000001", consecutive_declines=0)
        order = await _seed_order(db, phone_suffix="D1")
        order.offered_rider_id = rider.id
        await db.flush()

        result = await dispatch_service.respond_to_assignment(
            db, rider.id, order.id, None, accepted=False
        )

        await db.refresh(rider)
        assert rider.consecutive_declines == 1
        assert rider.performance_score == pytest.approx(1.0), "No penalty on first decline"
        assert result["status"] == "DECLINED_REGISTERED"

    @pytest.mark.asyncio
    async def test_decline_2_applies_performance_penalty(self, db):
        """
        Second decline: performance score is reduced by 0.1 (clamped to min 0.4).
        """
        rider = await _seed_rider(db, phone="9500000002", consecutive_declines=1)
        order = await _seed_order(db, phone_suffix="D2")
        order.offered_rider_id = rider.id
        await db.flush()

        result = await dispatch_service.respond_to_assignment(
            db, rider.id, order.id, None, accepted=False
        )

        await db.refresh(rider)
        assert rider.consecutive_declines == 2
        assert rider.performance_score == pytest.approx(0.9, abs=0.001), \
            f"Expected score 0.9 after 2nd decline, got {rider.performance_score}"
        assert result["status"] == "DECLINED_REGISTERED"

    @pytest.mark.asyncio
    async def test_decline_3_forces_assignment(self, db):
        """
        Third consecutive decline must force-assign the order directly,
        set mandatory_assignment_flag=True, reset consecutive_declines to 0,
        and emit a dispatch.mandatory_assignment outbox event.
        """
        rider = await _seed_rider(db, phone="9500000003", consecutive_declines=2)
        order = await _seed_order(db, phone_suffix="D3")
        order.offered_rider_id = rider.id
        await db.flush()

        result = await dispatch_service.respond_to_assignment(
            db, rider.id, order.id, None, accepted=False
        )

        await db.refresh(rider)
        await db.refresh(order)

        # Force-assigned
        assert result["status"] == "MANDATORY_ASSIGNED"
        assert order.assignment_status == "ASSIGNED"
        assert order.rider_id == rider.id

        # Rider flagged
        assert rider.mandatory_assignment_flag is True
        assert rider.consecutive_declines == 0  # reset after mandatory

        # Outbox event emitted
        events_res = await db.execute(
            select(OutboxEvent).where(OutboxEvent.event_type == "dispatch.mandatory_assignment")
        )
        events = events_res.scalars().all()
        assert len(events) >= 1, "Expected dispatch.mandatory_assignment outbox event"
        assert events[0].payload["rider_id"] == rider.id

    @pytest.mark.asyncio
    async def test_decline_3_idempotent_on_status(self, db):
        """
        After mandatory assignment, rider status must be ASSIGNED and not IDLE.
        """
        rider = await _seed_rider(db, phone="9500000004", consecutive_declines=2)
        order = await _seed_order(db, phone_suffix="D4")
        order.offered_rider_id = rider.id
        await db.flush()

        await dispatch_service.respond_to_assignment(
            db, rider.id, order.id, None, accepted=False
        )

        await db.refresh(rider)
        assert rider.status == "ASSIGNED", f"Expected ASSIGNED after mandatory, got {rider.status}"
        assert rider.is_available is False

    @pytest.mark.asyncio
    async def test_accept_resets_consecutive_declines(self, db):
        """Accepting an offer must reset consecutive_declines to 0."""
        rider = await _seed_rider(db, phone="9500000005", consecutive_declines=2)
        order = await _seed_order(db, phone_suffix="ACC")
        order.offered_rider_id = rider.id
        await db.flush()

        await dispatch_service.respond_to_assignment(
            db, rider.id, order.id, None, accepted=True
        )

        await db.refresh(rider)
        assert rider.consecutive_declines == 0, "Accepting must reset consecutive_declines"
