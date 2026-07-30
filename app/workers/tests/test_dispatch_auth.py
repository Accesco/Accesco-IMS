"""
tests/test_dispatch_auth.py
 Verify 401/403/200 behavior on every dispatch endpoint.
"""
from __future__ import annotations

import os
import tempfile
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from datetime import datetime, timezone, timedelta

import app.models  # noqa: F401 — register all ORM models
from app.main import app
from app.models.base import Base
from app.core.database import get_db
from app.models.auth import User, Role, user_roles
from app.models.rider import Rider
from app.models.store import Store
from app.models.order import Order
from app.modules.auth.service import AuthService
from app.modules.auth.schemas import UserCreate, UserLogin

_DB = os.path.join(tempfile.gettempdir(), "ims_auth_test.db")
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
    async def _override():
        yield db
    app.dependency_overrides[get_db] = _override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


async def _get_token(http_client: AsyncClient, db: AsyncSession, role_name: str) -> str:
    """Register a user with the given role and return a JWT token."""
    phone_suffix = {"Admin": "001", "StoreManager": "002", "Viewer": "003"}.get(role_name, "099")
    username = f"testuser_{role_name.lower()}"
    password = "TestPass123!"
    email = f"{username}@test.com"

    # Create role if it doesn't exist
    from sqlalchemy import select
    role_res = await db.execute(select(Role).where(Role.name == role_name))
    role = role_res.scalar_one_or_none()
    if not role:
        role = Role(name=role_name)
        db.add(role)
        await db.flush()

    # Register user
    reg_resp = await http_client.post("/api/v1/auth/register", json={
        "username": username,
        "email": email,
        "password": password,
        "full_name": f"Test {role_name}",
        "phone": f"99000000{phone_suffix}",
    })
    if reg_resp.status_code not in (200, 201, 400):  # 400 = already exists
        raise AssertionError(f"Registration failed: {reg_resp.status_code} {reg_resp.text}")

    # Assign role
    user_res = await db.execute(select(User).where(User.username == username))
    user = user_res.scalar_one_or_none()
    if user and role not in user.roles:
        user.roles.append(role)
        await db.flush()

    # Login
    login_resp = await http_client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password,
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    return login_resp.json()["access_token"]


async def _seed_order_and_rider(db: AsyncSession):
    """Seed minimal data for endpoint calls that need real rows."""
    store = Store(name="AuthTestStore", address="1 Main St", city="Mumbai", state="MH",
                  latitude=19.076, longitude=72.877)
    db.add(store)
    await db.flush()

    rider = Rider(
        name="AuthRider",
        phone="8800000001",
        is_available=True,
        status="IDLE",
        battery_level=80.0,
        performance_score=1.0,
        consecutive_declines=0,
        last_heartbeat_at=datetime.now(timezone.utc),
        shift_start_time=datetime.now(timezone.utc),
        shift_end_time=datetime.now(timezone.utc) + timedelta(hours=8),
    )
    db.add(rider)
    await db.flush()

    order = Order(
        customer_id=1,
        store_id=store.id,
        status="PENDING",
        total_amount=99.99,
        payment_status="PAID",
        latitude=19.076,
        longitude=72.877,
        delivery_zone="ZONE_A",
        sla_deadline=datetime.now(timezone.utc) + timedelta(hours=1),
        assignment_status="UNASSIGNED",
    )
    db.add(order)
    await db.commit()
    return order, rider


# ─── 401 Tests — No token at all ──────────────────────────────────────────────

class TestDispatchAuth401:
    @pytest.mark.asyncio
    async def test_assign_no_token_401(self, http_client, db):
        order, _ = await _seed_order_and_rider(db)
        resp = await http_client.post(f"/api/v1/dispatch/assign/{order.id}")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_respond_no_token_401(self, http_client, db):
        resp = await http_client.post("/api/v1/dispatch/rider/respond",
                                      json={"rider_id": 1, "accepted": True})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_heartbeat_no_token_401(self, http_client, db):
        resp = await http_client.post("/api/v1/dispatch/rider/heartbeat",
                                      json={"rider_id": 1, "latitude": 0.0, "longitude": 0.0, "battery_level": 80.0})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_transition_no_token_401(self, http_client, db):
        resp = await http_client.post("/api/v1/dispatch/rider/transition",
                                      json={"rider_id": 1, "target_state": "IDLE"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_sweep_no_token_401(self, http_client, db):
        resp = await http_client.post("/api/v1/dispatch/sweep")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_batches_no_token_401(self, http_client, db):
        resp = await http_client.get("/api/v1/dispatch/batches")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_batch_no_token_401(self, http_client, db):
        resp = await http_client.get("/api/v1/dispatch/batches/1")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_metrics_assignment_no_token_401(self, http_client, db):
        resp = await http_client.get("/api/v1/dispatch/metrics/assignment-accuracy")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_metrics_batch_fill_no_token_401(self, http_client, db):
        resp = await http_client.get("/api/v1/dispatch/metrics/batch-fill-rate")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_metrics_on_time_no_token_401(self, http_client, db):
        resp = await http_client.get("/api/v1/dispatch/metrics/on-time-rate")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_metrics_mape_no_token_401(self, http_client, db):
        resp = await http_client.get("/api/v1/dispatch/metrics/forecast-mape")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_metrics_utilisation_no_token_401(self, http_client, db):
        resp = await http_client.get("/api/v1/dispatch/metrics/rider-utilisation")
        assert resp.status_code == 401


# ─── 403 Tests — Wrong role ────────────────────────────────────────────────────

class TestDispatchAuth403:
    @pytest.mark.asyncio
    async def test_sweep_viewer_403(self, http_client, db):
        """POST /sweep requires Admin only — Viewer must get 403."""
        token = await _get_token(http_client, db, "Viewer")
        resp = await http_client.post(
            "/api/v1/dispatch/sweep",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}"

    @pytest.mark.asyncio
    async def test_sweep_storemanager_403(self, http_client, db):
        """POST /sweep requires Admin only — StoreManager must get 403."""
        token = await _get_token(http_client, db, "StoreManager")
        resp = await http_client.post(
            "/api/v1/dispatch/sweep",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403


# ─── 200 / Correct-Role Tests ─────────────────────────────────────────────────

class TestDispatchAuthPass:
    @pytest.mark.asyncio
    async def test_batches_list_viewer_200(self, http_client, db):
        """GET /batches is accessible to Viewer role."""
        token = await _get_token(http_client, db, "Viewer")
        resp = await http_client.get(
            "/api/v1/dispatch/batches",
            headers={"Authorization": f"Bearer {token}"}
        )
        # 200 with empty list is correct — no batches seeded
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_admin_200(self, http_client, db):
        """GET /metrics/* endpoints are accessible to Admin."""
        token = await _get_token(http_client, db, "Admin")
        for path in [
            "/api/v1/dispatch/metrics/assignment-accuracy",
            "/api/v1/dispatch/metrics/batch-fill-rate",
            "/api/v1/dispatch/metrics/on-time-rate",
            "/api/v1/dispatch/metrics/forecast-mape",
            "/api/v1/dispatch/metrics/rider-utilisation",
        ]:
            resp = await http_client.get(path, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200, f"Expected 200 on {path}, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_metrics_storemanager_200(self, http_client, db):
        """GET /metrics/* endpoints are accessible to StoreManager."""
        token = await _get_token(http_client, db, "StoreManager")
        resp = await http_client.get(
            "/api/v1/dispatch/metrics/on-time-rate",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_metrics_response_has_doc_b_thresholds(self, http_client, db):
        """Every metrics endpoint must include doc_b_baseline/target/goal keys."""
        token = await _get_token(http_client, db, "Admin")
        for path in [
            "/api/v1/dispatch/metrics/assignment-accuracy",
            "/api/v1/dispatch/metrics/batch-fill-rate",
            "/api/v1/dispatch/metrics/on-time-rate",
            "/api/v1/dispatch/metrics/forecast-mape",
            "/api/v1/dispatch/metrics/rider-utilisation",
        ]:
            resp = await http_client.get(path, headers={"Authorization": f"Bearer {token}"})
            data = resp.json()
            for key in ("doc_b_baseline", "doc_b_target", "doc_b_goal"):
                assert key in data, f"Missing '{key}' in {path} response: {data}"
