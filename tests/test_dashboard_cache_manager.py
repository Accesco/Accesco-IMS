import pytest
import json
from unittest.mock import AsyncMock, call, ANY
from app.modules.dashboard.cache import DashboardCacheManager


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.client = AsyncMock()
    return redis


@pytest.fixture
def cache_manager(mock_redis):
    return DashboardCacheManager(mock_redis)


# ── Key generation ────────────────────────────────────────────────────────────

def test_summary_key_no_filters(cache_manager):
    key = cache_manager.summary_key()
    assert key == "dashboard:summary"


def test_summary_key_with_filters_is_deterministic(cache_manager):
    filters = {"warehouse_id": 1, "zone": "A"}
    key1 = cache_manager.summary_key(filters)
    key2 = cache_manager.summary_key(filters)
    assert key1 == key2
    assert key1.startswith("dashboard:summary:")


def test_summary_key_different_filters_differ(cache_manager):
    key1 = cache_manager.summary_key({"warehouse_id": 1})
    key2 = cache_manager.summary_key({"warehouse_id": 2})
    assert key1 != key2


def test_activities_key_includes_pagination(cache_manager):
    key1 = cache_manager.activities_key(20, 0)
    key2 = cache_manager.activities_key(20, 20)
    assert key1 != key2


def test_revenue_chart_key(cache_manager):
    key = cache_manager.revenue_chart_key()
    assert key == "dashboard:charts:revenue"


def test_orders_chart_key(cache_manager):
    key = cache_manager.orders_chart_key()
    assert key == "dashboard:charts:orders"


def test_inventory_key(cache_manager):
    key = cache_manager.inventory_key()
    assert key == "dashboard:inventory"


# ── Invalidation patterns ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invalidate_summary_scans_correct_pattern(cache_manager, mock_redis):
    mock_redis.client.scan.side_effect = [(0, [])]
    await cache_manager.invalidate_summary()
    mock_redis.client.scan.assert_called_once_with(
        cursor="0", match="dashboard:summary*", count=100
    )


@pytest.mark.asyncio
async def test_invalidate_charts_scans_correct_pattern(cache_manager, mock_redis):
    mock_redis.client.scan.side_effect = [(0, [])]
    await cache_manager.invalidate_charts()
    mock_redis.client.scan.assert_called_once_with(
        cursor="0", match="dashboard:charts*", count=100
    )


@pytest.mark.asyncio
async def test_invalidate_inventory_scans_correct_pattern(cache_manager, mock_redis):
    mock_redis.client.scan.side_effect = [(0, [])]
    await cache_manager.invalidate_inventory()
    mock_redis.client.scan.assert_called_once_with(
        cursor="0", match="dashboard:inventory*", count=100
    )


@pytest.mark.asyncio
async def test_invalidate_all_scans_dashboard_wildcard(cache_manager, mock_redis):
    mock_redis.client.scan.side_effect = [(0, [])]
    await cache_manager.invalidate_all()
    mock_redis.client.scan.assert_called_once_with(
        cursor="0", match="dashboard:*", count=100
    )


@pytest.mark.asyncio
async def test_invalidate_deletes_matched_keys(cache_manager, mock_redis):
    mock_redis.client.scan.side_effect = [
        (1, ["dashboard:summary:abc"]),
        (0, ["dashboard:summary:def"]),
    ]
    await cache_manager.invalidate_summary()
    assert mock_redis.client.delete.call_count == 2
    mock_redis.client.delete.assert_any_call("dashboard:summary:abc")
    mock_redis.client.delete.assert_any_call("dashboard:summary:def")


@pytest.mark.asyncio
async def test_invalidate_no_matched_keys_does_not_call_delete(cache_manager, mock_redis):
    mock_redis.client.scan.side_effect = [(0, [])]
    await cache_manager.invalidate_summary()
    mock_redis.client.delete.assert_not_called()


@pytest.mark.asyncio
async def test_invalidate_handles_redis_error_gracefully(cache_manager, mock_redis):
    """A Redis failure during invalidation must not raise — it should be logged."""
    mock_redis.client.scan.side_effect = RuntimeError("Redis down")
    # Should not raise
    await cache_manager.invalidate_summary()
