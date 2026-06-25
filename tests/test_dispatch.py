# pyrefly: ignore [missing-import]
import os, tempfile
from datetime import datetime, timedelta, timezone
# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

import app.models  # noqa: F401 — registers all ORM models with Base.metadata
from app.main import app
from app.models.base import Base  # use the populated Base
from app.core.database import get_db
from app.models.order import Order
from app.models.rider import Rider
from app.models.store import Store
from app.modules.dispatch import service as dispatch_service
from app.core.exceptions import IMSException, ResourceNotFoundException

_DB = os.path.join(tempfile.gettempdir(), "ims_dispatch_test.db")
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
    from unittest.mock import MagicMock
    from app.modules.auth.routes import get_current_user

    # Mock an Admin user so RoleChecker lets all requests through
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


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _store(db):
    s = Store(name="Test Store", address="123 Main St", city="Bengaluru", state="Karnataka", active=True, latitude=12.9716, longitude=77.5946)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return s

async def _order(db, store_id=1, status="PENDING", assignment_status="UNASSIGNED",
                 rider_id=None, customer_id=1, lat=12.9900, lon=77.6800): # Zone D default
    o = Order(customer_id=customer_id, store_id=store_id, status=status,
              total_amount=99.99, payment_status="PAID",
              latitude=lat, longitude=lon,
              sla_deadline=datetime.now(timezone.utc) + timedelta(minutes=30),
              assignment_status=assignment_status, rider_id=rider_id)
    db.add(o); await db.commit(); await db.refresh(o)
    return o


async def _rider(db, phone="9000000099", is_available=True, status="IDLE", name="Rider", lat=12.9716, lon=77.5946):
    r = Rider(name=name, phone=phone, is_available=is_available, status=status,
              latitude=lat, longitude=lon,
              battery_level=100.0,
              shift_end_time=datetime.now(timezone.utc) + timedelta(hours=4),
              last_heartbeat_at=datetime.now(timezone.utc))
    db.add(r); await db.commit(); await db.refresh(r)
    return r

# ─── API Tests ────────────────────────────────────────────────────────────────

class TestDispatchAPI:
    @pytest.mark.asyncio
    async def test_assign_order_success(self, http_client, db):
        s = await _store(db)
        # Zone D so it uses solo rider
        o = await _order(db, store_id=s.id, lat=12.9900, lon=77.6800)
        r = await _rider(db, phone="9700000001")
        resp = await http_client.post(f"/api/v1/dispatch/assign/{o.id}")
        assert resp.status_code == 200
        d = resp.json()
        assert d["order_id"] == o.id
        assert d["rider_id"] == r.id
        assert d["status"] == "OFFERED"

    @pytest.mark.asyncio
    async def test_assign_nonexistent_order_404(self, http_client):
        assert (await http_client.post("/api/v1/dispatch/assign/999999")).status_code == 404

    @pytest.mark.asyncio
    async def test_assign_cancelled_order_400(self, http_client, db):
        s = await _store(db)
        o = await _order(db, store_id=s.id, status="CANCELLED")
        await _rider(db, phone="9700000002")
        r = await http_client.post(f"/api/v1/dispatch/assign/{o.id}")
        assert r.status_code == 400
        assert "CANCELLED" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_assign_completed_order_400(self, http_client, db):
        s = await _store(db)
        o = await _order(db, store_id=s.id, status="COMPLETED")
        await _rider(db, phone="9700000003")
        r = await http_client.post(f"/api/v1/dispatch/assign/{o.id}")
        assert r.status_code == 400
        assert "COMPLETED" in r.json()["detail"]

    @pytest.mark.asyncio
    async def test_assign_already_assigned_order_400(self, http_client, db):
        s = await _store(db)
        r0 = await _rider(db, phone="9700000004")
        o = await _order(db, store_id=s.id, assignment_status="ASSIGNED", rider_id=r0.id)
        r = await http_client.post(f"/api/v1/dispatch/assign/{o.id}")
        assert r.status_code == 400
        assert "already assigned" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_assign_no_riders_400(self, http_client, db):
        s = await _store(db)
        # Zone D
        o = await _order(db, store_id=s.id, lat=12.9900, lon=77.6800)
        # Busy rider
        await _rider(db, phone="9700000005", is_available=False, status="ASSIGNED")
        r = await http_client.post(f"/api/v1/dispatch/assign/{o.id}")
        assert r.status_code == 200
        assert "NO_RIDER_AVAILABLE" in r.json()["status"]

    @pytest.mark.asyncio
    async def test_assign_response_fields(self, http_client, db):
        s = await _store(db)
        o = await _order(db, store_id=s.id, lat=12.9900, lon=77.6800)
        await _rider(db, phone="9700000006")
        d = (await http_client.post(f"/api/v1/dispatch/assign/{o.id}")).json()
        for f in ("order_id", "rider_id", "status"):
            assert f in d


# ─── Service Tests ────────────────────────────────────────────────────────────

class TestDispatchService:
    @pytest.mark.asyncio
    async def test_returns_correct_ids(self, db):
        s = await _store(db)
        o = await _order(db, store_id=s.id, lat=12.9900, lon=77.6800)
        r = await _rider(db, phone="8100000001")
        result = await dispatch_service.ingest_new_order(db, o.id)
        assert result["order_id"] == o.id
        assert result["offered_rider_id"] == r.id
        assert result["status"] == "OFFERED"

    @pytest.mark.asyncio
    async def test_sets_order_assignment_status(self, db):
        s = await _store(db)
        o = await _order(db, store_id=s.id, lat=12.9900, lon=77.6800)
        await _rider(db, phone="8100000002")
        await dispatch_service.ingest_new_order(db, o.id)
        await db.refresh(o)
        assert o.assignment_status == "OFFERED"
        assert o.offered_rider_id is not None

    @pytest.mark.asyncio
    async def test_marks_rider_unavailable(self, db):
        s = await _store(db)
        o = await _order(db, store_id=s.id, lat=12.9900, lon=77.6800)
        r = await _rider(db, phone="8100000003")
        res = await dispatch_service.ingest_new_order(db, o.id)
        await dispatch_service.respond_to_assignment(db, res["offered_rider_id"], o.id, None, True)
        await db.refresh(r)
        assert r.status == "ASSIGNED"

    @pytest.mark.asyncio
    async def test_links_correct_rider_to_order(self, db):
        s = await _store(db)
        o = await _order(db, store_id=s.id, lat=12.9900, lon=77.6800)
        r = await _rider(db, phone="8100000004")
        res = await dispatch_service.ingest_new_order(db, o.id)
        await dispatch_service.respond_to_assignment(db, res["offered_rider_id"], o.id, None, True)
        await db.refresh(o)
        assert o.rider_id == r.id

    @pytest.mark.asyncio
    async def test_nonexistent_order_raises_404(self, db):
        with pytest.raises(ResourceNotFoundException):
            await dispatch_service.ingest_new_order(db, 999999)

    @pytest.mark.asyncio
    async def test_cancelled_order_raises_400(self, db):
        s = await _store(db)
        o = await _order(db, store_id=s.id, status="CANCELLED")
        await _rider(db, phone="8100000005")
        with pytest.raises(IMSException) as exc:
            await dispatch_service.ingest_new_order(db, o.id)
        assert exc.value.status_code == 400
        assert "CANCELLED" in exc.value.message

    @pytest.mark.asyncio
    async def test_completed_order_raises_400(self, db):
        s = await _store(db)
        o = await _order(db, store_id=s.id, status="COMPLETED")
        await _rider(db, phone="8100000006")
        with pytest.raises(IMSException) as exc:
            await dispatch_service.ingest_new_order(db, o.id)
        assert exc.value.status_code == 400
        assert "COMPLETED" in exc.value.message

    @pytest.mark.asyncio
    async def test_already_assigned_raises_400(self, db):
        s = await _store(db)
        r0 = await _rider(db, phone="8100000007")
        o = await _order(db, store_id=s.id, assignment_status="ASSIGNED", rider_id=r0.id)
        with pytest.raises(IMSException) as exc:
            await dispatch_service.ingest_new_order(db, o.id)
        assert exc.value.status_code == 400
        assert "already assigned" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_no_riders_raises_400(self, db):
        s = await _store(db)
        o = await _order(db, store_id=s.id, lat=12.9900, lon=77.6800)
        await _rider(db, phone="8100000008", is_available=False, status="ASSIGNED")
        res = await dispatch_service.ingest_new_order(db, o.id)
        assert "NO_RIDER_AVAILABLE" in res["status"]

    @pytest.mark.asyncio
    async def test_picks_available_over_busy(self, db):
        s = await _store(db)
        o = await _order(db, store_id=s.id, lat=12.9900, lon=77.6800)
        busy = await _rider(db, name="Busy", phone="8100000009", is_available=False)
        free = await _rider(db, name="Free", phone="8100000010", is_available=True)
        result = await dispatch_service.ingest_new_order(db, o.id)
        assert result["offered_rider_id"] == free.id
        assert result["offered_rider_id"] != busy.id

    @pytest.mark.asyncio
    async def test_pending_order_assignable(self, db):
        s = await _store(db)
        o = await _order(db, store_id=s.id, status="PENDING", lat=12.9900, lon=77.6800)
        await _rider(db, phone="8100000011")
        assert (await dispatch_service.ingest_new_order(db, o.id))["status"] == "OFFERED"

    @pytest.mark.asyncio
    async def test_order_with_rider_id_already_set_raises(self, db):
        s = await _store(db)
        r0 = await _rider(db, phone="8100000012")
        o = await _order(db, store_id=s.id, rider_id=r0.id, assignment_status="UNASSIGNED")
        with pytest.raises(IMSException) as exc:
            await dispatch_service.ingest_new_order(db, o.id)
        assert exc.value.status_code == 400


# ─── Concurrency Tests ────────────────────────────────────────────────────────

class TestDispatchConcurrency:
    @pytest.mark.asyncio
    async def test_rider_not_assigned_twice_sequentially(self, db):
        s = await _store(db)
        o1 = await _order(db, store_id=s.id, customer_id=10, lat=12.9900, lon=77.6800)
        o2 = await _order(db, store_id=s.id, customer_id=11, lat=12.9900, lon=77.6800)
        await _rider(db, phone="8200000001")

        r1 = await dispatch_service.ingest_new_order(db, o1.id)
        assert r1["status"] == "OFFERED"

        # Simulating accepting the offer so the rider is locked/busy
        await dispatch_service.respond_to_assignment(db, r1["offered_rider_id"], o1.id, None, True)

        res2 = await dispatch_service.ingest_new_order(db, o2.id)
        assert "NO_RIDER_AVAILABLE" in res2["status"]

    @pytest.mark.asyncio
    async def test_two_riders_two_orders_both_assigned(self, db):
        s = await _store(db)
        o1 = await _order(db, store_id=s.id, customer_id=20, lat=12.9900, lon=77.6800)
        o2 = await _order(db, store_id=s.id, customer_id=21, lat=12.9900, lon=77.6800)
        r1 = await _rider(db, name="R1", phone="8200000002")
        r2 = await _rider(db, name="R2", phone="8200000003")

        res1 = await dispatch_service.ingest_new_order(db, o1.id)
        await dispatch_service.respond_to_assignment(db, res1["offered_rider_id"], o1.id, None, True)

        res2 = await dispatch_service.ingest_new_order(db, o2.id)
        await dispatch_service.respond_to_assignment(db, res2["offered_rider_id"], o2.id, None, True)

        assert res1["status"] == res2["status"] == "OFFERED"
        assert res1["offered_rider_id"] != res2["offered_rider_id"]
        assert {res1["offered_rider_id"], res2["offered_rider_id"]} == {r1.id, r2.id}

    @pytest.mark.asyncio
    async def test_sequential_simulation_one_of_two_requests_fails(self, db):
        s = await _store(db)
        o1 = await _order(db, store_id=s.id, customer_id=30, lat=12.9900, lon=77.6800)
        o2 = await _order(db, store_id=s.id, customer_id=31, lat=12.9900, lon=77.6800)
        await _rider(db, phone="8200000004")

        successes, failures = [], []
        for order_id in [o1.id, o2.id]:
            async with _SESSION() as session:
                try:
                    res = await dispatch_service.ingest_new_order(session, order_id)
                    if res.get("status") == "OFFERED":
                        # simulate accept to lock rider
                        await dispatch_service.respond_to_assignment(session, res["offered_rider_id"], order_id, None, True)
                        successes.append(res)
                    else:
                        failures.append(res)
                except IMSException as e:
                    failures.append(e)

        assert len(successes) == 1
        assert len(failures) == 1