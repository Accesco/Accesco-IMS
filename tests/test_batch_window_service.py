"""
tests/test_batch_window_service.py
Batch Window Service Tests:
  - Holt-Winters output bounds (45–180s clamp)
  - Redis caching behavior (cache hit skips DB)
  - ForecastMetric row created on each window calculation (Task 2)
"""
from __future__ import annotations

import os
import tempfile
import pytest
import pytest_asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

import app.models  # noqa: F401
from app.models.base import Base
from app.models.community import Community
from app.models.store import Store
from app.models.order import Order
from app.models.forecast import ForecastMetric, CommunityDynamicWindow
from app.modules.dispatch.batch_window_service import BatchWindowOptimizer
from app.core.forecasting import predict_holt_winters, calculate_optimal_batch_window

_DB = os.path.join(tempfile.gettempdir(), "ims_batch_window_test.db")
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


def _make_redis(cached_value=None) -> MagicMock:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=str(cached_value) if cached_value else None)
    redis.set = AsyncMock()
    return redis


async def _seed_community(db: AsyncSession, community_id: str = "test-community-1") -> Community:
    comm = Community(
        id=community_id,
        name="Test Community",
        centroid_latitude=19.0,
        centroid_longitude=72.8,
        polygon={"type": "Polygon", "coordinates": [[[72.7, 18.9], [72.9, 18.9], [72.9, 19.1], [72.7, 19.1], [72.7, 18.9]]]},
        entry_points=[{"lat": 19.0, "lon": 72.8}],
        batch_window_sec=120,
        max_batch_size=4,
    )
    db.add(comm)
    await db.flush()
    return comm


async def _seed_store_and_order(db: AsyncSession, community_id: str) -> None:
    store = Store(name="BWStore", address="1 St", city="Mumbai", state="MH")
    db.add(store)
    await db.flush()
    order = Order(
        customer_id=1,
        store_id=store.id,
        status="PENDING",
        total_amount=10.0,
        payment_status="PAID",
        latitude=19.0,
        longitude=72.8,
        delivery_zone="ZONE_A",
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=1),
        assignment_status="UNASSIGNED",
        community_id=community_id,
    )
    db.add(order)
    await db.commit()


# ─── Holt-Winters Bounds Tests ─────────────────────────────────────────────────

class TestHoltWintersBounds:

    @pytest.mark.parametrize("series,expected_clamp", [
        # Very high order rate → window should clamp to 45s minimum
        ([50.0, 60.0, 80.0, 100.0, 150.0, 200.0], 45),
        # Very low order rate → window should clamp to 180s maximum
        ([0.1, 0.1, 0.1, 0.1, 0.1, 0.1], 180),
        # Moderate rate → within bounds [45, 180]
        ([1.0, 1.5, 1.2, 1.8, 2.0, 1.6], None),
    ])
    def test_calculate_optimal_batch_window_clamps(self, series, expected_clamp):
        predicted = predict_holt_winters(series, alpha=0.4, beta=0.3)
        per_min = predicted / 10.0
        window_sec, _ = calculate_optimal_batch_window(per_min)

        assert 45 <= window_sec <= 180, f"Window {window_sec}s outside [45, 180]"
        if expected_clamp is not None:
            assert window_sec == expected_clamp, f"Expected {expected_clamp}s clamp, got {window_sec}s"

    @pytest.mark.asyncio
    async def test_optimizer_always_returns_bounded_window(self, db):
        """BatchWindowOptimizer.determine_optimal_window_for_community must return a value in [45, 180]."""
        community_id = "bounds-test-community"
        await _seed_community(db, community_id)
        redis = _make_redis(cached_value=None)

        optimizer = BatchWindowOptimizer(db, redis)
        window = await optimizer.determine_optimal_window_for_community(community_id)

        assert 45 <= window <= 180, f"Window {window}s is outside [45, 180] bounds"


# ─── Redis Cache Tests ─────────────────────────────────────────────────────────

class TestBatchWindowCaching:

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_value_without_db_query(self, db):
        """If Redis has a cached value, no DB query should be made and cached value returned."""
        cached_window = 90
        redis = _make_redis(cached_value=cached_window)

        optimizer = BatchWindowOptimizer(db, redis)
        result = await optimizer.determine_optimal_window_for_community("any-community-id")

        assert result == cached_window
        # set() should NOT be called when we hit the cache
        redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_stores_result_in_redis(self, db):
        """On a cache miss, the computed window must be stored in Redis with 600s TTL."""
        community_id = "cache-miss-community"
        await _seed_community(db, community_id)
        redis = _make_redis(cached_value=None)

        optimizer = BatchWindowOptimizer(db, redis)
        window = await optimizer.determine_optimal_window_for_community(community_id)

        redis.set.assert_called_once_with(f"community:window:{community_id}", window, ex=600)



class TestForecastPersistence:

    @pytest.mark.asyncio
    async def test_forecast_metric_row_created_on_window_calculation(self, db):
        """
        Every call to determine_optimal_window_for_community must persist
        a ForecastMetric row (Task 2).
        """
        community_id = "forecast-persist-community"
        await _seed_community(db, community_id)
        await _seed_store_and_order(db, community_id)
        redis = _make_redis(cached_value=None)

        optimizer = BatchWindowOptimizer(db, redis)
        await optimizer.determine_optimal_window_for_community(community_id)

        result = await db.execute(select(ForecastMetric))
        metrics = result.scalars().all()
        assert len(metrics) >= 1, "Expected at least one ForecastMetric row to be created"

        metric = metrics[0]
        assert metric.predicted_orders_per_min >= 0
        assert 45 <= metric.recommended_batch_window_sec <= 180

    @pytest.mark.asyncio
    async def test_community_dynamic_window_row_created(self, db):
        """
        Every call to determine_optimal_window_for_community must persist
        a CommunityDynamicWindow row (Task 2).
        """
        community_id = "dynamic-window-persist-community"
        await _seed_community(db, community_id)
        redis = _make_redis(cached_value=None)

        optimizer = BatchWindowOptimizer(db, redis)
        await optimizer.determine_optimal_window_for_community(community_id)

        result = await db.execute(
            select(CommunityDynamicWindow).where(CommunityDynamicWindow.community_id == community_id)
        )
        windows = result.scalars().all()
        assert len(windows) >= 1, "Expected at least one CommunityDynamicWindow row"

        window = windows[0]
        assert window.community_id == community_id
        assert 0 <= window.hour_of_day <= 23
        assert 0 <= window.day_of_week <= 6
        assert 45 <= window.calculated_window_sec <= 180

    @pytest.mark.asyncio
    async def test_multiple_calls_create_multiple_forecast_rows(self, db):
        """Each cache-miss call should create a new ForecastMetric row."""
        community_id = "multi-forecast-community"
        await _seed_community(db, community_id)
        redis = _make_redis(cached_value=None)

        optimizer = BatchWindowOptimizer(db, redis)
        await optimizer.determine_optimal_window_for_community(community_id)
        await optimizer.determine_optimal_window_for_community(community_id)

        result = await db.execute(select(ForecastMetric))
        metrics = result.scalars().all()
        assert len(metrics) >= 2, "Expected 2 ForecastMetric rows for 2 cache-miss calls"
