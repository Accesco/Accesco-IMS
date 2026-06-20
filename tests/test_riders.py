"""
Tests for Rider Management — API + Service level
Issue #5
"""

import os, tempfile
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

import app.models  # noqa: F401 — registers all ORM models with Base.metadata
from app.main import app
from app.models.base import Base  # use the populated Base, not app.core.database's
from app.core.database import get_db
from app.models.rider import Rider
from app.modules.riders.service import RiderService
from app.modules.riders.repository import RiderRepository
from app.modules.riders.schemas import RiderCreate
from app.core.exceptions import IMSException

# File-based SQLite so all sessions in a test share the same data
_DB = os.path.join(tempfile.gettempdir(), "ims_riders_test.db")
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


@pytest_asyncio.fixture
async def seeded_rider(db: AsyncSession) -> Rider:
    r = Rider(name="Seeded", phone="9000000001", is_available=True, status="ONLINE")
    db.add(r); await db.commit(); await db.refresh(r)
    return r


@pytest_asyncio.fixture
async def unavailable_rider(db: AsyncSession) -> Rider:
    r = Rider(name="Busy", phone="9000000002", is_available=False, status="ASSIGNED")
    db.add(r); await db.commit(); await db.refresh(r)
    return r


# ─── API Tests ────────────────────────────────────────────────────────────────

class TestCreateRiderAPI:
    @pytest.mark.asyncio
    async def test_create_rider_success(self, http_client):
        resp = await http_client.post("/api/v1/riders", json={
            "name": "Ravi Kumar", "phone": "9876543210",
            "latitude": 28.6139, "longitude": 77.2090,
            "is_available": True, "status": "ONLINE",
        })
        assert resp.status_code == 200
        d = resp.json()
        assert d["name"] == "Ravi Kumar"
        assert d["phone"] == "9876543210"
        assert d["is_available"] is True
        assert d["status"] == "ONLINE"
        assert isinstance(d["id"], int)

    @pytest.mark.asyncio
    async def test_create_rider_persists_in_db(self, http_client):
        cid = (await http_client.post("/api/v1/riders", json={"name": "P", "phone": "9111111111"})).json()["id"]
        ids = [r["id"] for r in (await http_client.get("/api/v1/riders")).json()]
        assert cid in ids

    @pytest.mark.asyncio
    async def test_duplicate_phone_returns_400(self, http_client):
        p = {"name": "Orig", "phone": "9222222222"}
        await http_client.post("/api/v1/riders", json=p)
        r = await http_client.post("/api/v1/riders", json=p)
        assert r.status_code == 400
        assert "already exists" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_create_without_location(self, http_client):
        r = await http_client.post("/api/v1/riders", json={"name": "G", "phone": "9333333333"})
        assert r.status_code == 200
        assert r.json()["latitude"] is None
        assert r.json()["longitude"] is None

    @pytest.mark.asyncio
    async def test_default_status_online(self, http_client):
        r = await http_client.post("/api/v1/riders", json={"name": "D", "phone": "9444444444"})
        assert r.status_code == 200
        assert r.json()["status"] == "ONLINE"

    @pytest.mark.asyncio
    async def test_default_is_available_true(self, http_client):
        r = await http_client.post("/api/v1/riders", json={"name": "E", "phone": "9555555555"})
        assert r.status_code == 200
        assert r.json()["is_available"] is True

    @pytest.mark.asyncio
    async def test_missing_name_returns_422(self, http_client):
        assert (await http_client.post("/api/v1/riders", json={"phone": "9666666666"})).status_code == 422

    @pytest.mark.asyncio
    async def test_missing_phone_returns_422(self, http_client):
        assert (await http_client.post("/api/v1/riders", json={"name": "NoPhone"})).status_code == 422


class TestListRidersAPI:
    @pytest.mark.asyncio
    async def test_list_empty(self, http_client):
        r = await http_client.get("/api/v1/riders")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_list_returns_all(self, http_client):
        await http_client.post("/api/v1/riders", json={"name": "A", "phone": "9700000001"})
        await http_client.post("/api/v1/riders", json={"name": "B", "phone": "9700000002"})
        r = await http_client.get("/api/v1/riders")
        assert r.status_code == 200
        assert len(r.json()) == 2

    @pytest.mark.asyncio
    async def test_response_shape(self, http_client):
        await http_client.post("/api/v1/riders", json={"name": "S", "phone": "9800000001"})
        rider = (await http_client.get("/api/v1/riders")).json()[0]
        for f in ("id", "name", "phone", "is_available", "status"):
            assert f in rider


# ─── Service Tests ────────────────────────────────────────────────────────────

class TestRiderService:
    @pytest.mark.asyncio
    async def test_create_rider(self, db):
        r = await RiderService(db).create_rider(RiderCreate(name="Svc", phone="8000000001"))
        assert r.id is not None and r.name == "Svc"

    @pytest.mark.asyncio
    async def test_duplicate_phone_raises_400(self, db):
        svc = RiderService(db)
        await svc.create_rider(RiderCreate(name="F", phone="8000000002"))
        with pytest.raises(IMSException) as exc:
            await svc.create_rider(RiderCreate(name="S", phone="8000000002"))
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_get_all_empty(self, db):
        assert await RiderService(db).get_all_riders() == []

    @pytest.mark.asyncio
    async def test_get_all_includes_seeded(self, db, seeded_rider):
        riders = await RiderService(db).get_all_riders()
        assert any(r.id == seeded_rider.id for r in riders)

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, db, seeded_rider):
        r = await RiderService(db).get_rider(seeded_rider.id)
        assert r is not None and r.id == seeded_rider.id

    @pytest.mark.asyncio
    async def test_get_by_id_missing_returns_none(self, db):
        assert await RiderService(db).get_rider(99999) is None

    @pytest.mark.asyncio
    async def test_defaults_available_online(self, db):
        r = await RiderService(db).create_rider(RiderCreate(name="Fr", phone="8000000003"))
        assert r.is_available is True
        assert r.status == "ONLINE"


# ─── Repository Tests ─────────────────────────────────────────────────────────

class TestRiderRepository:
    @pytest.mark.asyncio
    async def test_available_excludes_unavailable(self, db, seeded_rider, unavailable_rider):
        avail = {r.id for r in await RiderRepository(db).get_available_riders()}
        assert seeded_rider.id in avail
        assert unavailable_rider.id not in avail

    @pytest.mark.asyncio
    async def test_available_empty_when_all_busy(self, db):
        db.add(Rider(name="Busy", phone="8100000001", is_available=False, status="ASSIGNED"))
        await db.commit()
        assert await RiderRepository(db).get_available_riders() == []

    @pytest.mark.asyncio
    async def test_get_by_id_missing_returns_none(self, db):
        assert await RiderRepository(db).get_rider_by_id(999999) is None