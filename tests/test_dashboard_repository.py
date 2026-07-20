import pytest
from app.modules.dashboard.repository import DashboardRepository

@pytest.mark.asyncio
async def test_get_orders_summary(db_session):
    repo = DashboardRepository(db_session)
    summary = await repo.get_orders_summary()
    assert "total" in summary
    assert "delivered" in summary
    assert "pending" in summary
    assert "cancelled" in summary
    assert "revenue" in summary

@pytest.mark.asyncio
async def test_count_orders(db_session):
    repo = DashboardRepository(db_session)
    count = await repo.count_orders()
    assert isinstance(count, int)

@pytest.mark.asyncio
async def test_get_inventory_summary(db_session):
    repo = DashboardRepository(db_session)
    summary = await repo.get_inventory_summary()
    assert "available" in summary
    assert "reserved" in summary
    assert "out_of_stock" in summary

@pytest.mark.asyncio
async def test_get_warehouse_metrics(db_session):
    repo = DashboardRepository(db_session)
    metrics = await repo.get_warehouse_metrics()
    assert isinstance(metrics, list)

@pytest.mark.asyncio
async def test_get_recent_activities(db_session):
    repo = DashboardRepository(db_session)
    activities = await repo.get_recent_activities(limit=5)
    assert "items" in activities
    assert "total" in activities
    assert isinstance(activities["items"], list)
