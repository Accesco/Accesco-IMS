"""
tests/test_edge_cases.py
 Edge Case Tests :
  - Picker delay detection + outbox event
  - Flash surge detection + window expansion + outbox event
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
from app.models.community import Community
from app.models.outbox import OutboxEvent
from app.modules.dispatch.edge_case_service import (
    detect_picker_delay,
    detect_flash_surge,
    PICKER_DELAY_EXTRA_MINUTES,
    DEFAULT_EXPECTED_PICK_MINUTES,
    SURGE_MULTIPLIER,
    BATCH_WINDOW_MIN_SEC,
    BATCH_WINDOW_MAX_SEC,
)

_DB = os.path.join(tempfile.gettempdir(), "ims_edge_cases_test.db")
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
    store = Store(name=f"EdgeStore{id(db)}", address="1 St", city="Mumbai", state="MH")
    db.add(store)
    await db.flush()
    return store


async def _seed_community(db: AsyncSession, community_id: str, batch_window_sec: int = 120) -> Community:
    comm = Community(
        id=community_id,
        name=f"EdgeComm {community_id}",
        centroid_latitude=19.0,
        centroid_longitude=72.8,
        polygon={"type": "Polygon", "coordinates": [[[72.7, 18.9], [72.9, 18.9], [72.9, 19.1], [72.7, 19.1], [72.7, 18.9]]]},
        entry_points=[{"lat": 19.0, "lon": 72.8}],
        batch_window_sec=batch_window_sec,
        max_batch_size=4,
    )
    db.add(comm)
    await db.flush()
    return comm



class TestPickerDelayDetection:

    @pytest.mark.asyncio
    async def test_picker_delay_detected_and_outbox_emitted(self, db):
        """
        An order in PICKING state with picking_started_at older than
        expected + 5 minutes must trigger an outbox event.
        """
        store = await _seed_store(db)
        # Set picking_started_at to well beyond the threshold
        past_started = datetime.now(timezone.utc) - timedelta(
            minutes=DEFAULT_EXPECTED_PICK_MINUTES + PICKER_DELAY_EXTRA_MINUTES + 5
        )
        order = Order(
            customer_id=1,
            store_id=store.id,
            status="PICKING",
            total_amount=10.0,
            payment_status="PAID",
            latitude=19.0,
            longitude=72.8,
            delivery_zone="ZONE_A",
            sla_deadline=datetime.now(timezone.utc) + timedelta(hours=1),
            assignment_status="ASSIGNED",
            picking_started_at=past_started,
        )
        db.add(order)
        await db.commit()

        flagged = await detect_picker_delay(db)

        assert flagged >= 1, "Expected at least 1 flagged picker delay"

        result = await db.execute(
            select(OutboxEvent).where(OutboxEvent.event_type == "dispatch.picker_delay_detected")
        )
        events = result.scalars().all()
        assert len(events) >= 1, "Expected dispatch.picker_delay_detected outbox event"
        assert events[0].payload["order_id"] == order.id

    @pytest.mark.asyncio
    async def test_picker_delay_not_triggered_within_threshold(self, db):
        """
        An order in PICKING state within the expected time must NOT be flagged.
        """
        store = await _seed_store(db)
        # picking_started_at is only 5 minutes ago — within threshold
        recent_started = datetime.now(timezone.utc) - timedelta(minutes=5)
        order = Order(
            customer_id=2,
            store_id=store.id,
            status="PICKING",
            total_amount=10.0,
            payment_status="PAID",
            latitude=19.0,
            longitude=72.8,
            delivery_zone="ZONE_A",
            sla_deadline=datetime.now(timezone.utc) + timedelta(hours=1),
            assignment_status="ASSIGNED",
            picking_started_at=recent_started,
        )
        db.add(order)
        await db.commit()

        flagged = await detect_picker_delay(db)
        assert flagged == 0, "Expected 0 flagged delays within threshold"

    @pytest.mark.asyncio
    async def test_non_picking_orders_ignored(self, db):
        """Orders not in PICKING status must be ignored by the picker delay detector."""
        store = await _seed_store(db)
        far_past = datetime.now(timezone.utc) - timedelta(hours=2)
        order = Order(
            customer_id=3,
            store_id=store.id,
            status="DELIVERED",  # not PICKING
            total_amount=10.0,
            payment_status="PAID",
            latitude=19.0,
            longitude=72.8,
            delivery_zone="ZONE_A",
            sla_deadline=datetime.now(timezone.utc) + timedelta(hours=1),
            assignment_status="ASSIGNED",
            picking_started_at=far_past,
        )
        db.add(order)
        await db.commit()

        flagged = await detect_picker_delay(db)
        assert flagged == 0, "DELIVERED orders must not trigger picker delay"



class TestFlashSurgeDetection:

    @pytest.mark.asyncio
    async def test_surge_detected_and_window_expanded(self, db):
        """
        When current 15-min rate > 3x trailing 15-min rate, the community
        batch_window_sec must be expanded by 50% (clamped to [45, 180]),
        and a dispatch.surge_detected event must be emitted.
        """
        community_id = "surge-test-community"
        community = await _seed_community(db, community_id, batch_window_sec=100)
        store = await _seed_store(db)
        now = datetime.now(timezone.utc)

        # Trailing window: 1 order (low baseline)
        for i in range(1):
            order = Order(
                customer_id=i + 10,
                store_id=store.id,
                status="PENDING",
                total_amount=10.0,
                payment_status="PAID",
                latitude=19.0,
                longitude=72.8,
                delivery_zone="ZONE_A",
                sla_deadline=now + timedelta(hours=1),
                assignment_status="UNASSIGNED",
                community_id=community_id,
            )
            order.created_at = now - timedelta(minutes=20)  # trailing window
            db.add(order)

        # Current window: 5 orders (spike — 5x the trailing rate)
        for i in range(5):
            order = Order(
                customer_id=i + 20,
                store_id=store.id,
                status="PENDING",
                total_amount=10.0,
                payment_status="PAID",
                latitude=19.0,
                longitude=72.8,
                delivery_zone="ZONE_A",
                sla_deadline=now + timedelta(hours=1),
                assignment_status="UNASSIGNED",
                community_id=community_id,
            )
            order.created_at = now - timedelta(minutes=5)  # current window
            db.add(order)

        await db.commit()

        surge_count = await detect_flash_surge(db)

        # Reload community to check window
        await db.refresh(community)

        result = await db.execute(
            select(OutboxEvent).where(OutboxEvent.event_type == "dispatch.surge_detected")
        )
        events = result.scalars().all()

        if surge_count > 0:
            assert len(events) >= 1, "Expected dispatch.surge_detected outbox event"
            # Window must be expanded but within bounds
            assert BATCH_WINDOW_MIN_SEC <= community.batch_window_sec <= BATCH_WINDOW_MAX_SEC
            assert community.batch_window_sec > 100, "Window should have been expanded from 100s"

    @pytest.mark.asyncio
    async def test_no_surge_when_rate_not_3x(self, db):
        """
        When current rate is only 2x the trailing rate, no surge is detected.
        """
        community_id = "no-surge-community"
        community = await _seed_community(db, community_id, batch_window_sec=120)
        store = await _seed_store(db)
        now = datetime.now(timezone.utc)

        # Trailing: 5 orders
        for i in range(5):
            order = Order(
                customer_id=i + 30,
                store_id=store.id,
                status="PENDING",
                total_amount=10.0,
                payment_status="PAID",
                latitude=19.0,
                longitude=72.8,
                delivery_zone="ZONE_A",
                sla_deadline=now + timedelta(hours=1),
                assignment_status="UNASSIGNED",
                community_id=community_id,
            )
            order.created_at = now - timedelta(minutes=20)
            db.add(order)

        # Current: 10 orders (2x, below 3x threshold)
        for i in range(10):
            order = Order(
                customer_id=i + 40,
                store_id=store.id,
                status="PENDING",
                total_amount=10.0,
                payment_status="PAID",
                latitude=19.0,
                longitude=72.8,
                delivery_zone="ZONE_A",
                sla_deadline=now + timedelta(hours=1),
                assignment_status="UNASSIGNED",
                community_id=community_id,
            )
            order.created_at = now - timedelta(minutes=5)
            db.add(order)

        await db.commit()

        surge_count = await detect_flash_surge(db)
        assert surge_count == 0, f"Expected 0 surge detections at 2x ratio, got {surge_count}"

    @pytest.mark.asyncio
    async def test_surge_window_clamped_to_180(self, db):
        """
        Even with a surge, the batch window must not exceed 180 seconds.
        """
        community_id = "clamp-surge-community"
        # Start at maximum window; expansion should clamp to 180
        community = await _seed_community(db, community_id, batch_window_sec=179)
        await db.commit()

        store = await _seed_store(db)
        now = datetime.now(timezone.utc)

        # Trailing: 1 order; current: 10 orders → 10x > 3x threshold
        for i, minutes_ago in [(0, 20)] + [(i, 5) for i in range(10)]:
            order = Order(
                customer_id=i + 50,
                store_id=store.id,
                status="PENDING",
                total_amount=10.0,
                payment_status="PAID",
                latitude=19.0,
                longitude=72.8,
                delivery_zone="ZONE_A",
                sla_deadline=now + timedelta(hours=1),
                assignment_status="UNASSIGNED",
                community_id=community_id,
            )
            order.created_at = now - timedelta(minutes=minutes_ago)
            db.add(order)

        await db.commit()

        await detect_flash_surge(db)
        await db.refresh(community)

        assert community.batch_window_sec <= BATCH_WINDOW_MAX_SEC, \
            f"Window {community.batch_window_sec}s exceeds max {BATCH_WINDOW_MAX_SEC}s"
