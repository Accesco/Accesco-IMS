"""
End-to-end integration tests for the full order → dispatch lifecycle.

Verifies: order creation → status transitions → rider assignment →
pickup → transit → delivery, with state synchronization across
order, rider, and assignment records.
"""

import os
import tempfile
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

import app.models  # noqa: F401
from app.main import app
from app.models.base import Base
from app.core.database import get_db
from app.modules.auth.routes import get_current_user
from app.models.order import Order
from app.models.rider import Rider
from app.models.store import Store
from app.models.product import Product
from app.modules.dispatch import service as dispatch_service
from app.modules.orders.service import OrderService
from app.core.exceptions import IMSException

_DB = os.path.join(tempfile.gettempdir(), "ims_integration_test.db")
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


@pytest_asyncio.fixture
async def http_client(db: AsyncSession):
    mock_role = MagicMock(); mock_role.name = "Admin"
    mock_user = MagicMock(); mock_user.roles = [mock_role]; mock_user.id = 1

    async def _override_db():
        yield db

    async def _override_auth():
        return mock_user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_auth
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)


async def _create_store(db):
    s = Store(
        name="Integration Store", address="Test Addr", city="Bengaluru",
        state="Karnataka", active=True, latitude=12.9716, longitude=77.5946,
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s


async def _create_product(db, sku="INT-P1"):
    p = Product(sku=sku, name=f"Product {sku}", category="Test", unit="pcs", active=True)
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _create_rider(db, phone="9000000099"):
    r = Rider(
        name="Integration Rider", phone=phone, is_available=True, status="IDLE",
        latitude=12.9716, longitude=77.5946, battery_level=100.0,
        shift_end_time=datetime.now(timezone.utc) + timedelta(hours=4),
        last_heartbeat_at=datetime.now(timezone.utc),
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return r


# ─── Full Lifecycle Service Test ──────────────────────────────────────────────

class TestFullLifecycleService:
    """Tests the complete order → assign → pickup → transit → deliver flow at service level."""

    @pytest.mark.asyncio
    async def test_complete_lifecycle(self, db):
        store = await _create_store(db)
        product = await _create_product(db)
        rider = await _create_rider(db)

        # 1. Create order
        order = Order(
            customer_id=1, store_id=store.id, status="PENDING",
            total_amount=100.0, payment_status="COMPLETED",
            latitude=12.99, longitude=77.68,  # Zone D
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            assignment_status="UNASSIGNED",
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        # Verify initial state
        assert order.status == "PENDING"
        assert order.assignment_status == "UNASSIGNED"
        assert order.rider_id is None

        # 2. Assign rider via dispatch engine
        result = await dispatch_service.ingest_new_order(db, order.id)
        assert result["status"] == "OFFERED"
        assert result["offered_rider_id"] == rider.id

        # 3. Accept assignment
        accept_result = await dispatch_service.respond_to_assignment(
            db, rider.id, order.id, None, True
        )
        assert accept_result["status"] == "ORDER_ACCEPTED"

        await db.refresh(order)
        await db.refresh(rider)

        # Verify assignment state
        assert order.rider_id == rider.id
        assert order.assignment_status == "ASSIGNED"
        assert order.status == "RIDER_ASSIGNED"
        assert rider.status == "ASSIGNED"

        # 4. Pickup
        order = await dispatch_service.pickup_order(db, order.id)
        await db.refresh(rider)

        assert order.status == "PICKED_UP"
        assert rider.status == "EN_ROUTE_PICKUP"

        # 5. In transit
        order = await dispatch_service.start_transit(db, order.id)
        await db.refresh(rider)

        assert order.status == "IN_TRANSIT"
        assert rider.status == "DELIVERING"

        # 6. Delivered
        order = await dispatch_service.deliver_order(db, order.id)
        await db.refresh(rider)

        assert order.status == "DELIVERED"
        assert order.assignment_status == "COMPLETED"
        assert rider.status == "RETURNING"
        assert rider.is_available is True


class TestLifecycleValidation:
    """Tests that invalid lifecycle transitions are properly rejected."""

    @pytest.mark.asyncio
    async def test_cannot_pickup_pending_order(self, db):
        store = await _create_store(db)
        rider = await _create_rider(db, phone="9100000001")

        order = Order(
            customer_id=1, store_id=store.id, status="PENDING",
            total_amount=50.0, payment_status="COMPLETED",
            latitude=12.99, longitude=77.68,
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            assignment_status="UNASSIGNED", rider_id=rider.id,
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        with pytest.raises(IMSException) as exc:
            await dispatch_service.pickup_order(db, order.id)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_deliver_without_transit(self, db):
        store = await _create_store(db)
        rider = await _create_rider(db, phone="9100000002")

        order = Order(
            customer_id=1, store_id=store.id, status="PICKED_UP",
            total_amount=50.0, payment_status="COMPLETED",
            latitude=12.99, longitude=77.68,
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            assignment_status="ASSIGNED", rider_id=rider.id,
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        with pytest.raises(IMSException) as exc:
            await dispatch_service.deliver_order(db, order.id)
        assert exc.value.status_code == 400
        assert "IN_TRANSIT" in exc.value.message

    @pytest.mark.asyncio
    async def test_cannot_fail_delivered_order(self, db):
        store = await _create_store(db)

        order = Order(
            customer_id=1, store_id=store.id, status="DELIVERED",
            total_amount=50.0, payment_status="COMPLETED",
            latitude=12.99, longitude=77.68,
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            assignment_status="COMPLETED",
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        with pytest.raises(IMSException) as exc:
            await dispatch_service.fail_delivery(db, order.id)
        assert exc.value.status_code == 400


# ─── API-Level Lifecycle Tests ────────────────────────────────────────────────

class TestLifecycleAPI:
    @pytest.mark.asyncio
    async def test_lifecycle_api_endpoints(self, http_client, db):
        store = await _create_store(db)
        rider = await _create_rider(db, phone="9200000001")

        # Create an order in RIDER_ASSIGNED state (simulating post-assignment)
        order = Order(
            customer_id=1, store_id=store.id, status="RIDER_ASSIGNED",
            total_amount=75.0, payment_status="COMPLETED",
            latitude=12.99, longitude=77.68,
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            assignment_status="ASSIGNED", rider_id=rider.id,
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        # Set rider to ASSIGNED state
        rider.status = "ASSIGNED"
        await db.commit()

        # Pickup
        resp = await http_client.post(f"/api/v1/dispatch/{order.id}/pickup")
        assert resp.status_code == 200
        data = resp.json()
        assert data["order_status"] == "PICKED_UP"
        assert data["rider_id"] == rider.id

        # In transit
        resp = await http_client.post(f"/api/v1/dispatch/{order.id}/in-transit")
        assert resp.status_code == 200
        assert resp.json()["order_status"] == "IN_TRANSIT"

        # Delivered
        resp = await http_client.post(f"/api/v1/dispatch/{order.id}/delivered")
        assert resp.status_code == 200
        assert resp.json()["order_status"] == "DELIVERED"

        # Verify final DB state
        await db.refresh(order)
        await db.refresh(rider)
        assert order.status == "DELIVERED"
        assert order.assignment_status == "COMPLETED"
        assert rider.is_available is True

    @pytest.mark.asyncio
    async def test_fail_delivery_api(self, http_client, db):
        store = await _create_store(db)
        rider = await _create_rider(db, phone="9200000002")
        rider.status = "DELIVERING"

        order = Order(
            customer_id=1, store_id=store.id, status="IN_TRANSIT",
            total_amount=50.0, payment_status="COMPLETED",
            latitude=12.99, longitude=77.68,
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            assignment_status="ASSIGNED", rider_id=rider.id,
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        resp = await http_client.post(f"/api/v1/dispatch/{order.id}/failed")
        assert resp.status_code == 200
        assert resp.json()["order_status"] == "FAILED"

        await db.refresh(order)
        assert order.status == "FAILED"
        assert order.assignment_status == "FAILED"


# ─── Order Status Transition Tests ────────────────────────────────────────────

class TestOrderStatusTransitions:
    @pytest.mark.asyncio
    async def test_valid_status_transition_via_api(self, http_client, db):
        store = await _create_store(db)

        order = Order(
            customer_id=1, store_id=store.id, status="PENDING",
            total_amount=50.0, payment_status="PENDING",
            latitude=12.97, longitude=77.59,
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            assignment_status="UNASSIGNED",
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        # PENDING → CONFIRMED
        resp = await http_client.patch(
            f"/api/v1/orders/{order.id}/status",
            json={"status": "CONFIRMED"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CONFIRMED"

        # CONFIRMED → READY_FOR_DISPATCH
        resp = await http_client.patch(
            f"/api/v1/orders/{order.id}/status",
            json={"status": "READY_FOR_DISPATCH"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "READY_FOR_DISPATCH"

    @pytest.mark.asyncio
    async def test_invalid_status_transition_rejected(self, http_client, db):
        store = await _create_store(db)

        order = Order(
            customer_id=1, store_id=store.id, status="PENDING",
            total_amount=50.0, payment_status="PENDING",
            latitude=12.97, longitude=77.59,
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            assignment_status="UNASSIGNED",
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        # PENDING → DELIVERED (invalid skip)
        resp = await http_client.patch(
            f"/api/v1/orders/{order.id}/status",
            json={"status": "DELIVERED"},
        )
        assert resp.status_code == 400
        assert "Invalid status transition" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_terminal_state_blocks_transitions(self, http_client, db):
        store = await _create_store(db)

        order = Order(
            customer_id=1, store_id=store.id, status="CANCELLED",
            total_amount=50.0, payment_status="REFUNDED",
            latitude=12.97, longitude=77.59,
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            assignment_status="UNASSIGNED",
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)

        resp = await http_client.patch(
            f"/api/v1/orders/{order.id}/status",
            json={"status": "CONFIRMED"},
        )
        assert resp.status_code == 400
        assert "terminal state" in resp.json()["detail"].lower() or "none" in resp.json()["detail"].lower()


# ─── Order List / Filter Tests ────────────────────────────────────────────────

class TestOrderListFilters:
    @pytest.mark.asyncio
    async def test_list_orders_paginated(self, http_client, db):
        store = await _create_store(db)
        for i in range(5):
            db.add(Order(
                customer_id=1, store_id=store.id, status="PENDING",
                total_amount=10.0 * (i + 1), payment_status="PENDING",
                latitude=12.97, longitude=77.59,
                sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
                assignment_status="UNASSIGNED",
            ))
        await db.commit()

        resp = await http_client.get("/api/v1/orders?limit=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["orders"]) == 3
        assert data["limit"] == 3

    @pytest.mark.asyncio
    async def test_filter_by_status(self, http_client, db):
        store = await _create_store(db)
        db.add(Order(
            customer_id=1, store_id=store.id, status="PENDING",
            total_amount=10.0, payment_status="PENDING",
            latitude=12.97, longitude=77.59,
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            assignment_status="UNASSIGNED",
        ))
        db.add(Order(
            customer_id=1, store_id=store.id, status="DELIVERED",
            total_amount=20.0, payment_status="COMPLETED",
            latitude=12.97, longitude=77.59,
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            assignment_status="COMPLETED",
        ))
        await db.commit()

        resp = await http_client.get("/api/v1/orders?status=DELIVERED")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["orders"][0]["status"] == "DELIVERED"

    @pytest.mark.asyncio
    async def test_filter_by_store_id(self, http_client, db):
        store = await _create_store(db)
        db.add(Order(
            customer_id=1, store_id=store.id, status="PENDING",
            total_amount=10.0, payment_status="PENDING",
            latitude=12.97, longitude=77.59,
            sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
            assignment_status="UNASSIGNED",
        ))
        await db.commit()

        resp = await http_client.get(f"/api/v1/orders?store_id={store.id}")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        resp_none = await http_client.get("/api/v1/orders?store_id=99999")
        assert resp_none.json()["total"] == 0
