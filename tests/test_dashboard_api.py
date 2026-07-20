import pytest
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.modules.auth.routes import get_current_user
from app.models.auth import User, Role
from app.modules.dashboard.dependencies import get_dashboard_service
from app.modules.dashboard.schemas import (
    DashboardSummaryResponse,
    RevenueChartResponse,
    RevenueTrend,
    ActivitiesResponse,
    WarehousePerformanceResponse,
    WarehousePerformance
)

client = TestClient(app)

def mock_get_current_user():
    return User(id=1, email="test@test.com", roles=[Role(name="ADMIN")])

def mock_dashboard_service():
    mock_service = AsyncMock()
    mock_service.get_summary.return_value = DashboardSummaryResponse(
        total_orders=10, revenue=500, pending_orders=2, inventory_accuracy=99,
        sla=95, csat=4.5, returns=0, delivered_orders=8
    )
    mock_service.get_revenue_charts.return_value = RevenueChartResponse(
        daily=[RevenueTrend(date="2026-07-15", amount=100)],
        weekly=[], monthly=[], yearly=[]
    )
    mock_service.get_activities.return_value = ActivitiesResponse(
        activities=[], total=0, page=2, page_size=5
    )
    mock_service.get_warehouses.return_value = WarehousePerformanceResponse(
        warehouses=[WarehousePerformance(
            store_id=1, name="Store 1", orders=10, revenue=500, inventory=100, sla=95
        )]
    )
    return mock_service

@pytest.fixture(autouse=True)
def override_deps():
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_dashboard_service] = mock_dashboard_service
    yield
    app.dependency_overrides.clear()

def test_get_dashboard_summary_authorized():
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "totalOrders" in data["data"]

def test_get_dashboard_revenue_charts():
    response = client.get("/api/v1/dashboard/charts/revenue")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "daily" in data["data"]

def test_get_dashboard_activities_pagination():
    response = client.get("/api/v1/dashboard/activities?page=2&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["page"] == 2
    assert data["data"]["pageSize"] == 5

def test_get_dashboard_warehouses_with_filters():
    response = client.get("/api/v1/dashboard/warehouses?warehouse_id=1")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"]["warehouses"], list)

def test_get_dashboard_summary_unauthorized():
    app.dependency_overrides.pop(get_current_user)
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 401
