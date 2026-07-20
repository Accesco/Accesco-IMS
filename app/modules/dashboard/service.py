import json
import logging
from typing import Dict, Any, List, Optional

from app.modules.dashboard.provider import DashboardProvider
from app.modules.dashboard.cache import DashboardCacheManager
from app.core.redis import RedisService
from app.modules.dashboard.schemas import (
    DashboardSummaryResponse,
    RevenueChartResponse,
    RevenueTrend,
    OrdersChartResponse,
    InventoryChartResponse,
    WarehousePerformanceResponse,
    WarehousePerformance,
    ActivitiesResponse,
    ActivityItem,
    AlertsResponse
)

logger = logging.getLogger("dashboard.service")

class DashboardService:
    def __init__(self, provider: DashboardProvider, redis: RedisService):
        self.provider = provider
        self.redis = redis
        self.cache_manager = DashboardCacheManager(redis)

    async def _get_cached_or_fetch(self, cache_key: str, ttl: int, fetch_func, response_model):
        try:
            cached_data = await self.redis.get(cache_key)
            if cached_data:
                logger.info(f"CACHE HIT: {cache_key}")
                data_dict = json.loads(cached_data)
                return response_model(**data_dict)
        except Exception as e:
            logger.warning(f"Failed to read from cache for {cache_key}: {e}")

        logger.info(f"CACHE MISS: {cache_key}")
        result = await fetch_func()

        try:
            serialized = result.model_dump(by_alias=True)
            await self.redis.set(cache_key, json.dumps(serialized), expire=ttl)
        except Exception as e:
            logger.warning(f"Failed to write to cache for {cache_key}: {e}")

        return result

    async def get_summary(self, filters: Optional[Dict[str, Any]] = None) -> DashboardSummaryResponse:
        cache_key = self.cache_manager.summary_key(filters)
        
        async def fetcher():
            data = await self.provider.get_summary_data(filters)
            orders = data.get("orders", {})
            total_orders = orders.get("total", 0)
            delivered_orders = orders.get("delivered", 0)
            
            sla = 0.0
            if total_orders > 0:
                sla = round((delivered_orders / total_orders) * 100, 2)
                
            return DashboardSummaryResponse(
                total_orders=total_orders,
                revenue=orders.get("revenue", 0.0),
                pending_orders=orders.get("pending", 0),
                inventory_accuracy=99.0,
                sla=sla,
                csat=4.8,
                returns=0,
                delivered_orders=delivered_orders
            )
            
        return await self._get_cached_or_fetch(cache_key, 60, fetcher, DashboardSummaryResponse)

    async def get_revenue_charts(self, filters: Optional[Dict[str, Any]] = None) -> RevenueChartResponse:
        cache_key = self.cache_manager.revenue_chart_key(filters)
        
        async def fetcher():
            trends = await self.provider.get_revenue_trends(filters)
            daily = [RevenueTrend(date=t["date"], amount=t["amount"]) for t in trends]
            return RevenueChartResponse(
                daily=daily,
                weekly=daily,
                monthly=daily,
                yearly=daily
            )
            
        return await self._get_cached_or_fetch(cache_key, 60, fetcher, RevenueChartResponse)

    async def get_orders_chart(self, filters: Optional[Dict[str, Any]] = None) -> OrdersChartResponse:
        cache_key = self.cache_manager.orders_chart_key(filters)
        
        async def fetcher():
            orders = await self.provider.get_orders_trends(filters)
            return OrdersChartResponse(
                created=orders.get("total", 0),
                completed=orders.get("delivered", 0),
                pending=orders.get("pending", 0),
                cancelled=orders.get("cancelled", 0)
            )
            
        return await self._get_cached_or_fetch(cache_key, 60, fetcher, OrdersChartResponse)

    async def get_inventory_chart(self, filters: Optional[Dict[str, Any]] = None) -> InventoryChartResponse:
        cache_key = self.cache_manager.inventory_key(filters)
        
        async def fetcher():
            inv = await self.provider.get_inventory_status(filters)
            return InventoryChartResponse(
                available=inv.get("available", 0),
                reserved=inv.get("reserved", 0),
                damaged=inv.get("damaged", 0),
                out_of_stock=inv.get("out_of_stock", 0)
            )
            
        return await self._get_cached_or_fetch(cache_key, 30, fetcher, InventoryChartResponse)

    async def get_warehouses(self, filters: Optional[Dict[str, Any]] = None) -> WarehousePerformanceResponse:
        cache_key = self.cache_manager.warehouses_key(filters)
        
        async def fetcher():
            metrics = await self.provider.get_warehouse_performance(filters)
            warehouses = [
                WarehousePerformance(
                    store_id=m["store_id"],
                    name=m["name"],
                    orders=m["orders"],
                    revenue=m["revenue"],
                    inventory=m["inventory"],
                    sla=m["sla"]
                )
                for m in metrics
            ]
            return WarehousePerformanceResponse(warehouses=warehouses)
            
        return await self._get_cached_or_fetch(cache_key, 60, fetcher, WarehousePerformanceResponse)

    async def get_activities(self, limit: int, offset: int, filters: Optional[Dict[str, Any]] = None) -> ActivitiesResponse:
        cache_key = self.cache_manager.activities_key(limit, offset, filters)
        
        async def fetcher():
            result = await self.provider.get_activities(limit, offset, filters)
            activities = []
            for row in result.get("items", []):
                activities.append(
                    ActivityItem(
                        id=row.id,
                        action=row.action,
                        module=row.module,
                        created_at=row.created_at,
                        entity_id=row.entity_id
                    )
                )
            return ActivitiesResponse(
                activities=activities,
                total=result.get("total", 0),
                page=(offset // limit) + 1 if limit else 1,
                page_size=limit
            )
            
        return await self._get_cached_or_fetch(cache_key, 15, fetcher, ActivitiesResponse)

    async def get_alerts(self, limit: int, offset: int, filters: Optional[Dict[str, Any]] = None) -> AlertsResponse:
        cache_key = self.cache_manager.alerts_key(limit, offset, filters)
        
        async def fetcher():
            return AlertsResponse(
                alerts=[],
                total=0,
                page=(offset // limit) + 1 if limit else 1,
                page_size=limit
            )
            
        return await self._get_cached_or_fetch(cache_key, 15, fetcher, AlertsResponse)
