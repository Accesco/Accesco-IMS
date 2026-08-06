# tests/test_stores_and_orders.py
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

# Adjust imports to match your test configuration
from app.main import app
from app.core.geo_utils import classify_zone_and_sla, haversine_distance
from app.core.database import get_db

@pytest_asyncio.fixture
async def http_client(db_session: AsyncSession):
    from app.modules.stores.routes import admin_or_manager, all_authorized
    from app.modules.auth.routes import get_current_user
    from types import SimpleNamespace
    
    async def _override_get_db():
        yield db_session

    async def _mock_admin():
        return SimpleNamespace(id=1, username="admin", email="admin@example.com", role=SimpleNamespace(name="Admin"))
        
    async def _mock_current_user():
        return SimpleNamespace(id=2, username="user", email="user@example.com", role=SimpleNamespace(name="Customer"))

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[admin_or_manager] = _mock_admin
    app.dependency_overrides[all_authorized] = _mock_admin
    app.dependency_overrides[get_current_user] = _mock_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_store_coordinates_flow(http_client: AsyncClient):
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
    response = await http_client.post("/api/v1/stores", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["latitude"] == 12.9600
    assert data["longitude"] == 77.6400
    store_id = data["id"]

    # 2. Verify Store Retrieval returns coordinates
    get_res = await http_client.get(f"/api/v1/stores/{store_id}")
    assert get_res.status_code == 200
    assert get_res.json()["latitude"] == 12.9600

    # 3. Update coordinates with validation error check (Latitude out of range via PUT)
    bad_payload = {"latitude": 150.0}
    # Fixed: Changed from client.post to client.put
    bad_res = await http_client.put(f"/api/v1/stores/{store_id}", json=bad_payload)
    assert bad_res.status_code == 400  # Should trigger coordinate validation exception

    # 4. Correct coordinates update
    good_payload = {"latitude": 12.9550, "longitude": 77.6350}
    upd_res = await http_client.put(f"/api/v1/stores/{store_id}", json=good_payload)
    assert upd_res.status_code == 200
    assert upd_res.json()["latitude"] == 12.9550


@pytest.mark.asyncio
async def test_order_placement_coordinate_integration(http_client: AsyncClient):
    # Create a store without coordinates to test failure behavior
    store_no_coords = {
        "name": "Coordinateless Store",
        "address": "Secret St",
        "city": "Bengaluru",
        "state": "Karnataka",
        "active": True
    }
    st_res = await http_client.post("/api/v1/stores", json=store_no_coords)
    store_id_fail = st_res.json()["id"]

    # Order creation should fail when store coordinates are missing
    order_fail_payload = {
        "store_id": store_id_fail,
        "latitude": 12.9612,
        "longitude": 77.6415,
        "items": [{"product_id": 1, "quantity": 1, "price": 10.0}]
    }
    fail_res = await http_client.post("/api/v1/orders", json=order_fail_payload)
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