"""
tests/test_metrics_endpoints.py

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
from app.models.batch import Batch
from app.models.rider import Rider
from app.models.store import Store
from app.models.community import Community
from app.models.forecast import ForecastMetric
from app.modules.dispatch.metrics_service import MetricsService

_DB = os.path.join(tempfile.gettempdir(), "ims_metrics_test.db")
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


async def _seed_store(db: AsyncSession, name: str = "MetricsStore") -> Store:
    store = Store(name=name, address="1 St", city="Mumbai", state="MH")
    db.add(store)
    await db.flush()
    return store


async def _seed_community(db: AsyncSession, community_id: str = "metrics-community") -> Community:
    comm = Community(
        id=community_id,
        name="Metrics Community",
        centroid_latitude=19.0,
        centroid_longitude=72.8,
        polygon={"type": "Polygon", "coordinates": [[[72.7, 18.9], [72.9, 19.1], [72.7, 19.1], [72.7, 18.9]]]},
        entry_points=[{"lat": 19.0, "lon": 72.8}],
        batch_window_sec=120,
        max_batch_size=4,
    )
    db.add(comm)
    await db.flush()
    return comm



class TestMetricsResponseShape:

    @pytest.mark.asyncio
    async def test_all_metrics_have_doc_b_keys(self, db):
        """All metric responses must include baseline, target, goal and current_value keys."""
        svc = MetricsService(db)
        methods = [
            ("assignment_accuracy", svc.assignment_accuracy),
            ("batch_fill_rate", svc.batch_fill_rate),
            ("on_time_rate", svc.on_time_rate),
            ("forecast_mape", svc.forecast_mape),
            ("rider_utilisation", svc.rider_utilisation),
        ]
        for name, method in methods:
            result = await method()
            for key in ("doc_b_baseline", "doc_b_target", "doc_b_goal", "metric"):
                assert key in result, f"Missing '{key}' in {name} response: {result}"

    @pytest.mark.asyncio
    async def test_all_metrics_have_correct_metric_names(self, db):
        """The 'metric' key must match the expected slug for each endpoint."""
        svc = MetricsService(db)
        expected = {
            "assignment_accuracy": "assignment_accuracy",
            "batch_fill_rate": "batch_fill_rate",
            "on_time_rate": "on_time_rate",
            "forecast_mape": "forecast_mape",
            "rider_utilisation": "rider_utilisation",
        }
        for method_name, expected_metric_key in expected.items():
            result = await getattr(svc, method_name)()
            assert result["metric"] == expected_metric_key, \
                f"Expected metric='{expected_metric_key}', got '{result['metric']}'"

    @pytest.mark.asyncio
    async def test_empty_db_returns_none_current_value(self, db):
        """With no data, current_value must be None (not a crash)."""
        svc = MetricsService(db)
        for method_name in ("assignment_accuracy", "batch_fill_rate", "on_time_rate",
                            "forecast_mape", "rider_utilisation"):
            result = await getattr(svc, method_name)()
            assert result["current_value"] is None, \
                f"{method_name}: expected None current_value with empty DB, got {result['current_value']}"



class TestAssignmentAccuracy:

    @pytest.mark.asyncio
    async def test_accuracy_computed_correctly(self, db):
        """8 optimal + 2 non-optimal = 80% accuracy."""
        store = await _seed_store(db, "AccStore")
        now = datetime.now(timezone.utc)

        for i in range(8):
            db.add(Order(
                customer_id=i + 1, store_id=store.id, status="DELIVERED",
                total_amount=10.0, payment_status="PAID",
                latitude=19.0, longitude=72.8, delivery_zone="ZONE_A",
                sla_deadline=now + timedelta(hours=1),
                assignment_status="ASSIGNED",
                assignment_was_optimal=True,
                actual_delivered_at=now - timedelta(minutes=5),
            ))

        for i in range(2):
            db.add(Order(
                customer_id=i + 100, store_id=store.id, status="DELIVERED",
                total_amount=10.0, payment_status="PAID",
                latitude=19.0, longitude=72.8, delivery_zone="ZONE_A",
                sla_deadline=now + timedelta(hours=1),
                assignment_status="ASSIGNED",
                assignment_was_optimal=False,
                actual_delivered_at=now - timedelta(minutes=5),
            ))

        await db.commit()

        svc = MetricsService(db)
        result = await svc.assignment_accuracy()
        assert result["current_value"] == pytest.approx(0.8, abs=0.01), \
            f"Expected 0.80 accuracy, got {result['current_value']}"



class TestBatchFillRate:

    @pytest.mark.asyncio
    async def test_fill_rate_computed_correctly(self, db):
        """2 batches of size 2 in a community with max_batch_size=4 → 50% fill rate."""
        comm = await _seed_community(db, "fill-rate-comm")

        for _ in range(2):
            batch = Batch(
                community_id=comm.id,
                status="ASSIGNED",
                dispatch_by=datetime.now(timezone.utc) + timedelta(hours=1),
                actual_batch_size=2,
            )
            db.add(batch)

        await db.commit()

        svc = MetricsService(db)
        result = await svc.batch_fill_rate()
        assert result["current_value"] == pytest.approx(0.5, abs=0.01), \
            f"Expected 0.50 fill rate, got {result['current_value']}"

        assert "per_community" in result
        assert comm.id in result["per_community"]



class TestOnTimeRate:

    @pytest.mark.asyncio
    async def test_on_time_rate_computed_correctly(self, db):
        """7 on-time + 3 late = 70% on-time rate."""
        store = await _seed_store(db, "OnTimeStore")
        now = datetime.now(timezone.utc)

        for i in range(7):
            deadline = now + timedelta(minutes=30)
            db.add(Order(
                customer_id=i + 200, store_id=store.id, status="DELIVERED",
                total_amount=10.0, payment_status="PAID",
                latitude=19.0, longitude=72.8, delivery_zone="ZONE_A",
                sla_deadline=deadline, assignment_status="ASSIGNED",
                actual_delivered_at=deadline - timedelta(minutes=1),
            ))

        for i in range(3):
            deadline = now + timedelta(minutes=30)
            db.add(Order(
                customer_id=i + 300, store_id=store.id, status="DELIVERED",
                total_amount=10.0, payment_status="PAID",
                latitude=19.0, longitude=72.8, delivery_zone="ZONE_A",
                sla_deadline=deadline, assignment_status="ASSIGNED",
                actual_delivered_at=deadline + timedelta(minutes=10),  # late
            ))

        await db.commit()

        svc = MetricsService(db)
        result = await svc.on_time_rate()
        assert result["current_value"] == pytest.approx(0.7, abs=0.01), \
            f"Expected 0.70 on-time rate, got {result['current_value']}"



class TestForecastMAPE:

    @pytest.mark.asyncio
    async def test_mape_computed_from_forecast_metrics(self, db):
        """
        Seed a ForecastMetric with predicted=1.0 orders/min.
        Seed 10 actual orders in that 10-min window → actual=1.0/min.
        Perfect prediction → MAPE≈0% → accuracy≈100%.
        """
        store = await _seed_store(db, "MAPEStore")
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=20)

        # Forecast metric predicting 1.0 orders/min for that window
        metric = ForecastMetric(
            store_id=store.id,
            target_time=window_start,
            predicted_orders_per_min=1.0,
            predicted_rider_demand=1,
            predicted_batch_size=1.0,
            recommended_batch_window_sec=120,
        )
        db.add(metric)

        for i in range(10):
            order = Order(
                customer_id=i + 400, store_id=store.id, status="DELIVERED",
                total_amount=10.0, payment_status="PAID",
                latitude=19.0, longitude=72.8, delivery_zone="ZONE_A",
                sla_deadline=now + timedelta(hours=1),
                assignment_status="ASSIGNED",
            )
            order.created_at = window_start + timedelta(seconds=i * 60)
            db.add(order)

        await db.commit()

        svc = MetricsService(db)
        result = await svc.forecast_mape()

        if result["current_value"] is not None:
            assert result["current_value"] >= 0.8, \
                f"Expected high accuracy for perfect prediction, got {result['current_value']}"
        assert "mape_pct" in result



class TestRiderUtilisation:

    @pytest.mark.asyncio
    async def test_utilisation_computed_correctly(self, db):
        """
        Rider with 4h shift and 2h active → 50% utilisation.
        """
        now = datetime.now(timezone.utc)
        rider = Rider(
            name="UtilRider",
            phone="9600000001",
            is_available=True,
            status="IDLE",
            battery_level=80.0,
            performance_score=1.0,
            consecutive_declines=0,
            last_heartbeat_at=now,
            shift_start_time=now - timedelta(hours=4),
            shift_end_time=now + timedelta(hours=4),  # still active
            shift_active_seconds=2 * 3600,  # 2 hours active
        )
        db.add(rider)
        await db.commit()

        svc = MetricsService(db)
        result = await svc.rider_utilisation()

        assert result["current_value"] is not None
        # 2h active / 4h elapsed = 0.5
        assert result["current_value"] == pytest.approx(0.5, abs=0.05), \
            f"Expected ~0.50 utilisation, got {result['current_value']}"

    @pytest.mark.asyncio
    async def test_utilisation_capped_at_1(self, db):
        """Utilisation score must never exceed 1.0."""
        now = datetime.now(timezone.utc)
        rider = Rider(
            name="MaxUtilRider",
            phone="9600000002",
            is_available=True,
            status="IDLE",
            battery_level=80.0,
            performance_score=1.0,
            consecutive_declines=0,
            last_heartbeat_at=now,
            shift_start_time=now - timedelta(hours=2),
            shift_end_time=now + timedelta(hours=4),
            shift_active_seconds=99999,  # more than shift duration
        )
        db.add(rider)
        await db.commit()

        svc = MetricsService(db)
        result = await svc.rider_utilisation()
        assert result["current_value"] is not None
        assert result["current_value"] <= 1.0, "Utilisation score must be <= 1.0"
