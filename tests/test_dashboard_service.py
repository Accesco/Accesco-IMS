import pytest
import json
from unittest.mock import AsyncMock, patch
from app.modules.dashboard.service import DashboardService
from app.modules.dashboard.provider import DashboardProvider
from app.modules.dashboard.schemas import DashboardSummaryResponse

@pytest.mark.asyncio
async def test_get_summary_cache_miss():
    mock_repo = AsyncMock()
    mock_provider = DashboardProvider(mock_repo)
    mock_provider.get_summary_data = AsyncMock(return_value={
        "orders": {"total": 100, "delivered": 90, "revenue": 5000.0}
    })
    
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # Cache miss
    
    service = DashboardService(mock_provider, mock_redis)
    summary = await service.get_summary()
    
    # Assert data was fetched from provider
    mock_provider.get_summary_data.assert_called_once()
    
    # Assert data was set in cache
    mock_redis.set.assert_called_once()
    assert summary.total_orders == 100
    assert summary.revenue == 5000.0

@pytest.mark.asyncio
async def test_get_summary_cache_hit():
    mock_repo = AsyncMock()
    mock_provider = DashboardProvider(mock_repo)
    mock_provider.get_summary_data = AsyncMock()
    
    cached_data = {
        "totalOrders": 200,
        "revenue": 10000.0,
        "pendingOrders": 10,
        "inventoryAccuracy": 99.0,
        "sla": 98.0,
        "csat": 4.9,
        "returns": 1,
        "deliveredOrders": 190
    }
    
    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps(cached_data)  # Cache hit
    
    service = DashboardService(mock_provider, mock_redis)
    summary = await service.get_summary()
    
    # Assert provider was NOT called
    mock_provider.get_summary_data.assert_not_called()
    assert summary.total_orders == 200
    assert summary.revenue == 10000.0

@pytest.mark.asyncio
async def test_invalidate_cache():
    from app.modules.dashboard.cache import DashboardCacheManager

    mock_redis = AsyncMock()
    mock_redis.client = AsyncMock()
    # Simulate a two-phase SCAN: first call returns a cursor + matched keys, second call signals end
    mock_redis.client.scan.side_effect = [
        (1, ["dashboard:summary:abc"]),
        (0, ["dashboard:summary:xyz"]),
    ]

    cache_manager = DashboardCacheManager(mock_redis)
    await cache_manager.invalidate_summary()

    # SCAN should have been called twice until cursor == 0
    assert mock_redis.client.scan.call_count == 2
    # Both batches should have been deleted
    assert mock_redis.client.delete.call_count == 2
