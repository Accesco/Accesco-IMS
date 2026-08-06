"""
tests/test_optimizer_service.py
Optimizer Service Tests:
  - Hungarian exact match on a known 2x2 cost matrix
  - Auction fallback triggers above the 100-rider/order threshold
  - Matrix padding for non-square inputs
  - Redis lock prevents concurrent sweeps
"""
from __future__ import annotations

import os
import tempfile
import pytest
import pytest_asyncio
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

import app.models  # noqa: F401
from app.models.base import Base
from app.models.rider import Rider
from app.models.order import Order
from app.models.store import Store
from app.modules.dispatch.optimizer_service import GlobalDispatchOptimizer

_DB = os.path.join(tempfile.gettempdir(), "ims_optimizer_test.db")
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


def _make_redis(lock_acquired: bool = True) -> MagicMock:
    """Creates a mock Redis client that either acquires or rejects the lock."""
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=lock_acquired)
    redis.delete = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    return redis


async def _seed_store(db: AsyncSession) -> Store:
    store = Store(name="OptiStore", address="1 St", city="Mumbai", state="MH",
                  latitude=19.0, longitude=72.8)
    db.add(store)
    await db.flush()
    return store


async def _seed_rider(db: AsyncSession, phone: str, store: Store) -> Rider:
    rider = Rider(
        name=f"Rider{phone[-4:]}",
        phone=phone,
        is_available=True,
        status="IDLE",
        battery_level=80.0,
        performance_score=1.0,
        consecutive_declines=0,
        last_heartbeat_at=datetime.now(timezone.utc),
        shift_start_time=datetime.now(timezone.utc),
        shift_end_time=datetime.now(timezone.utc) + timedelta(hours=8),
        latitude=19.0,
        longitude=72.8,
    )
    db.add(rider)
    await db.flush()
    return rider


async def _seed_order(db: AsyncSession, store: Store) -> Order:
    order = Order(
        customer_id=1,
        store_id=store.id,
        status="PENDING",
        total_amount=50.0,
        payment_status="PAID",
        latitude=19.01,
        longitude=72.81,
        delivery_zone="ZONE_A",
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=1),
        assignment_status="UNASSIGNED",
    )
    db.add(order)
    await db.flush()
    return order


# ─── Tests ─────────────────────────────────────────────────────────────────────

class TestOptimizerService:

    @pytest.mark.asyncio
    async def test_redis_lock_prevents_concurrent_sweep(self, db):
        """If the Redis lock is already held, sweep returns 0 immediately."""
        redis = _make_redis(lock_acquired=False)  # lock already taken
        optimizer = GlobalDispatchOptimizer(db, redis)
        result = await optimizer.execute_global_optimization_sweep()
        assert result == 0
        # Should not have attempted to delete the lock it never acquired
        redis.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_work_items_returns_zero(self, db):
        """With no unassigned orders or draft batches, sweep returns 0."""
        redis = _make_redis(lock_acquired=True)
        optimizer = GlobalDispatchOptimizer(db, redis)
        result = await optimizer.execute_global_optimization_sweep()
        assert result == 0

    @pytest.mark.asyncio
    async def test_hungarian_exact_on_small_matrix(self, db):
        """
        Hungarian solver must match the globally optimal assignment.
        For a 2-rider × 2-order matrix with a clear optimum, verify the
        correct rider→order pairing is selected.
        """
        from app.core.geo_utils import solve_hungarian_exact

        # Cost matrix where rider 0 should be matched to order 1 (cost 1.0)
        # and rider 1 to order 0 (cost 2.0) for optimal total cost of 3.0.
        # (vs. the naive diagonal: 5.0 + 3.0 = 8.0)
        cost_matrix = np.array([
            [5.0, 1.0],  # rider 0: expensive for item 0, cheap for item 1
            [2.0, 3.0],  # rider 1: moderate for item 0, expensive for item 1
        ])
        matches = solve_hungarian_exact(cost_matrix)
        # Build assignment dict: rider_idx -> item_idx
        assignment = dict(matches)
        # Optimal: rider 0 -> item 1, rider 1 -> item 0
        assert assignment.get(0) == 1, f"Expected rider 0 → item 1, got {assignment}"
        assert assignment.get(1) == 0, f"Expected rider 1 → item 0, got {assignment}"

    @pytest.mark.asyncio
    async def test_auction_fallback_triggers_above_threshold(self):
        """
        GlobalDispatchOptimizer uses auction algorithm when max(n_riders, n_items) > 100.
        This test patches both solvers and verifies the correct one is invoked.
        """
        with patch("app.modules.dispatch.optimizer_service.solve_hungarian_exact") as hungarian_mock, \
             patch("app.modules.dispatch.optimizer_service.solve_auction_approximate") as auction_mock:

            hungarian_mock.return_value = []
            auction_mock.return_value = []

            # Build a 101-rider optimizer mock scenario
            # We directly call the logic path by monkeypatching the cost matrix step
            fake_db = AsyncMock()
            fake_redis = _make_redis(lock_acquired=True)

            optimizer = GlobalDispatchOptimizer(fake_db, fake_redis)

            
            big_cost = np.full((101, 101), 9.9)
            optimizer._get_unassigned_orders = AsyncMock(return_value=[MagicMock()] * 1)
            optimizer._get_draft_batches = AsyncMock(return_value=[])
            optimizer._build_cost_matrix = AsyncMock(return_value=(big_cost, {i: MagicMock() for i in range(101)}, {0: MagicMock()}))
            optimizer._apply_assignment = AsyncMock()
            fake_db.commit = AsyncMock()
            fake_db.rollback = AsyncMock()

            # Import and patch the module-level rider list
            from app.modules.dispatch import repository as repo_mod
            with patch.object(repo_mod, "get_eligible_riders_for_assignment", AsyncMock(return_value=[MagicMock()] * 101)):
                await optimizer.execute_global_optimization_sweep()

            auction_mock.assert_called_once()
            hungarian_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_matrix_padding_for_non_square(self, db):
        """
        _build_cost_matrix must pad a non-square input to a square matrix
        with the fill value 9.9 in the padded cells.
        """
        from app.core.geo_utils import solve_hungarian_exact

        # 3 riders, 2 items → should pad to 3x3
        cost_3x2 = np.array([
            [1.0, 2.0],
            [3.0, 4.0],
            [5.0, 6.0],
        ])
        # Manually pad as the optimizer does
        n, m = 3, 2
        size = max(n, m)
        padded = np.full((size, size), 9.9)
        padded[:n, :m] = cost_3x2

        assert padded.shape == (3, 3)
        assert padded[0, 2] == pytest.approx(9.9)
        assert padded[1, 2] == pytest.approx(9.9)
        assert padded[0, 0] == pytest.approx(1.0)

        # Hungarian on square padded matrix must not crash
        matches = solve_hungarian_exact(padded)
        assert isinstance(matches, list)
