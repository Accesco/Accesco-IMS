import pytest
from unittest.mock import AsyncMock
from app.modules.dashboard.provider import DashboardProvider


@pytest.fixture
def mock_repo():
    repo = AsyncMock()
    repo.get_orders_summary.return_value = {
        "total": 50, "delivered": 40, "pending": 5, "cancelled": 5, "revenue": 2500.0
    }
    repo.get_inventory_summary.return_value = {
        "available": 100, "reserved": 20, "damaged": 0, "out_of_stock": 2
    }
    repo.get_revenue_data.return_value = [
        {"date": "2026-07-01", "amount": 1000.0},
        {"date": "2026-07-02", "amount": 1500.0},
    ]
    repo.get_warehouse_metrics.return_value = [
        {"store_id": 1, "name": "Main", "orders": 50, "revenue": 2500.0, "inventory": 100, "sla": 95.0}
    ]
    repo.get_recent_activities.return_value = {"items": [], "total": 0}
    repo.get_active_alerts.return_value = {"items": [], "total": 0}
    return repo


@pytest.fixture
def provider(mock_repo):
    return DashboardProvider(mock_repo)


@pytest.mark.asyncio
async def test_get_summary_data_delegates_to_repo(provider, mock_repo):
    result = await provider.get_summary_data()
    mock_repo.get_orders_summary.assert_called_once_with(None)
    mock_repo.get_inventory_summary.assert_called_once_with(None)
    assert result["orders"]["total"] == 50
    assert result["inventory"]["available"] == 100


@pytest.mark.asyncio
async def test_get_summary_data_passes_filters(provider, mock_repo):
    filters = {"warehouse_id": 1}
    await provider.get_summary_data(filters)
    mock_repo.get_orders_summary.assert_called_once_with(filters)
    mock_repo.get_inventory_summary.assert_called_once_with(filters)


@pytest.mark.asyncio
async def test_get_revenue_trends_delegates_to_repo(provider, mock_repo):
    result = await provider.get_revenue_trends()
    mock_repo.get_revenue_data.assert_called_once_with(None)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_orders_trends_delegates_to_repo(provider, mock_repo):
    result = await provider.get_orders_trends()
    mock_repo.get_orders_summary.assert_called_once_with(None)
    assert result["delivered"] == 40


@pytest.mark.asyncio
async def test_get_inventory_status_delegates_to_repo(provider, mock_repo):
    result = await provider.get_inventory_status()
    mock_repo.get_inventory_summary.assert_called_once_with(None)
    assert result["out_of_stock"] == 2


@pytest.mark.asyncio
async def test_get_warehouse_performance_delegates_to_repo(provider, mock_repo):
    result = await provider.get_warehouse_performance()
    mock_repo.get_warehouse_metrics.assert_called_once_with(None)
    assert result[0]["name"] == "Main"


@pytest.mark.asyncio
async def test_get_activities_passes_limit_offset(provider, mock_repo):
    await provider.get_activities(limit=5, offset=10)
    mock_repo.get_recent_activities.assert_called_once_with(5, 10, None)


@pytest.mark.asyncio
async def test_get_alerts_passes_limit_offset(provider, mock_repo):
    await provider.get_alerts(limit=5, offset=0)
    mock_repo.get_active_alerts.assert_called_once_with(5, 0, None)
