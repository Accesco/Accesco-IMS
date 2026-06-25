# tests/test_stores_and_orders.py
from __future__ import annotations

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

# Adjust imports to match your test configuration
from app.main import app
from app.core.geo_utils import classify_zone_and_sla, haversine_distance
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import MagicMock
from app.modules.auth.routes import get_current_user
from app.core.database import get_db

@pytest_asyncio.fixture
async def http_client(db_session: AsyncSession):
    mock_role = MagicMock(); mock_role.name = "Admin"
    mock_user = MagicMock(); mock_user.roles = [mock_role]; mock_user.id = 1

    async def _override_db():
        yield db_session

    async def _override_auth():
        return mock_user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_auth
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def admin_token_headers():
    return {"Authorization": "Bearer admin_token"}

@pytest.fixture
def user_token_headers():
    return {"Authorization": "Bearer user_token"}

@pytest.mark.asyncio
async def test_store_coordinates_flow(http_client: AsyncClient, admin_token_headers: dict):
    # 1. Create a Store with Coordinates
    payload = {
        "name": "Domlur Dark Store Test",
        "address": "12, 100 Feet Rd",
        "city": "Bengaluru",
        "state": "Karnataka",
        "latitude": 12.9600,
        "longitude": 77.6400,
        "active": True
    }
    response = await http_client.post("/api/v1/stores", json=payload, headers=admin_token_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["latitude"] == 12.9600
    assert data["longitude"] == 77.6400
    store_id = data["id"]

    # 2. Verify Store Retrieval returns coordinates
    get_res = await http_client.get(f"/api/v1/stores/{store_id}", headers=admin_token_headers)
    assert get_res.status_code == 200
    assert get_res.json()["latitude"] == 12.9600

    # 3. Update coordinates with validation error check (Latitude out of range via PUT)
    bad_payload = {"latitude": 150.0}
    # Fixed: Changed from client.post to client.put
    bad_res = await http_client.put(f"/api/v1/stores/{store_id}", json=bad_payload, headers=admin_token_headers)
    assert bad_res.status_code == 400  # Should trigger coordinate validation exception

    # 4. Correct coordinates update
    good_payload = {"latitude": 12.9550, "longitude": 77.6350}
    upd_res = await http_client.put(f"/api/v1/stores/{store_id}", json=good_payload, headers=admin_token_headers)
    assert upd_res.status_code == 200
    assert upd_res.json()["latitude"] == 12.9550


@pytest.mark.asyncio
async def test_order_placement_coordinate_integration(
    http_client: AsyncClient,
    user_token_headers: dict,
    admin_token_headers: dict
):
    # Create a store without coordinates to test failure behavior
    store_no_coords = {
        "name": "Coordinateless Store",
        "address": "Secret St",
        "city": "Bengaluru",
        "state": "Karnataka",
        "active": True
    }
    st_res = await http_client.post("/api/v1/stores", json=store_no_coords, headers=admin_token_headers)
    store_id_fail = st_res.json()["id"]

    # Order creation should fail when store coordinates are missing
    order_fail_payload = {
        "store_id": store_id_fail,
        "latitude": 12.9612,
        "longitude": 77.6415,
        "items": [{"product_id": 1, "quantity": 1, "price": 10.0}]
    }
    fail_res = await http_client.post("/api/v1/orders", json=order_fail_payload, headers=user_token_headers)
    assert fail_res.status_code == 400
    assert "coordinates configured" in fail_res.json()["detail"]


def test_geo_zone_assignment():
    # Test Zone classification based on store coordinates: 12.9600, 77.6400
    store_lat, store_lon = 12.9600, 77.6400

    # 1. ZONE_A (< 1 km distance)
    zone_a_lat, zone_a_lon = 12.9605, 77.6415  # ~200 meters away
    dist_a = haversine_distance(store_lat, store_lon, zone_a_lat, zone_a_lon)
    zone, sla = classify_zone_and_sla(dist_a)
    assert zone == "ZONE_A"
    assert sla == 8

    # 2. ZONE_B (1 - 2 km distance)
    zone_b_lat, zone_b_lon = 12.9700, 77.6490  # ~1.48 km away
    dist_b = haversine_distance(store_lat, store_lon, zone_b_lat, zone_b_lon)
    zone, sla = classify_zone_and_sla(dist_b)
    assert zone == "ZONE_B"
    assert sla == 12

    # 3. ZONE_D (4 - 6 km distance)
    zone_d_lat, zone_d_lon = 12.9900, 77.6800  # ~5.43 km away
    dist_d = haversine_distance(store_lat, store_lon, zone_d_lat, zone_d_lon)
    zone, sla = classify_zone_and_sla(dist_d)
    assert zone == "ZONE_D"
    assert sla == 25