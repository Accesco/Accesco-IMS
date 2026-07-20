import json
import hashlib
import logging
from typing import Dict, Any, Optional, List
from app.core.redis import RedisService

logger = logging.getLogger("dashboard.cache")

class DashboardCacheManager:
    def __init__(self, redis: RedisService):
        self.redis = redis

    def _generate_cache_key(self, base_key: str, filters: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        key_parts = [base_key]
        if filters:
            sorted_filters = sorted(filters.items())
            filter_str = json.dumps(sorted_filters)
            key_parts.append(hashlib.md5(filter_str.encode()).hexdigest()[:8])
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            kwarg_str = json.dumps(sorted_kwargs)
            key_parts.append(hashlib.md5(kwarg_str.encode()).hexdigest()[:8])
        return ":".join(key_parts)

    def summary_key(self, filters: Optional[Dict[str, Any]] = None) -> str:
        return self._generate_cache_key("dashboard:summary", filters)

    def revenue_chart_key(self, filters: Optional[Dict[str, Any]] = None) -> str:
        return self._generate_cache_key("dashboard:charts:revenue", filters)

    def orders_chart_key(self, filters: Optional[Dict[str, Any]] = None) -> str:
        return self._generate_cache_key("dashboard:charts:orders", filters)

    def inventory_key(self, filters: Optional[Dict[str, Any]] = None) -> str:
        return self._generate_cache_key("dashboard:inventory", filters)

    def warehouses_key(self, filters: Optional[Dict[str, Any]] = None) -> str:
        return self._generate_cache_key("dashboard:warehouses", filters)

    def activities_key(self, limit: int, offset: int, filters: Optional[Dict[str, Any]] = None) -> str:
        return self._generate_cache_key("dashboard:activities", filters, limit=limit, offset=offset)

    def alerts_key(self, limit: int, offset: int, filters: Optional[Dict[str, Any]] = None) -> str:
        return self._generate_cache_key("dashboard:alerts", filters, limit=limit, offset=offset)

    async def _invalidate_pattern(self, pattern: str) -> None:
        try:
            cursor = "0"
            while cursor != 0:
                cursor, matched_keys = await self.redis.client.scan(cursor=cursor, match=pattern, count=100)
                if matched_keys:
                    await self.redis.client.delete(*matched_keys)
            logger.info(f"Invalidated cache keys matching pattern: {pattern}")
        except Exception as e:
            logger.error(f"Failed to invalidate cache pattern {pattern}: {e}")

    async def invalidate_summary(self) -> None:
        await self._invalidate_pattern("dashboard:summary*")

    async def invalidate_charts(self) -> None:
        await self._invalidate_pattern("dashboard:charts*")

    async def invalidate_inventory(self) -> None:
        await self._invalidate_pattern("dashboard:inventory*")

    async def invalidate_all(self) -> None:
        await self._invalidate_pattern("dashboard:*")
