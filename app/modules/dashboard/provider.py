from typing import Dict, Any, List, Optional
from app.modules.dashboard.repository import DashboardRepositoryProtocol

class DashboardProvider:
    def __init__(self, repository: DashboardRepositoryProtocol):
        self.repository = repository

    async def get_summary_data(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Orchestrates fetching data required for the main dashboard summary."""
        orders_data = await self.repository.get_orders_summary(filters)
        inventory_data = await self.repository.get_inventory_summary(filters)
        
        return {
            "orders": orders_data,
            "inventory": inventory_data
        }

    async def get_revenue_trends(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return await self.repository.get_revenue_data(filters)

    async def get_orders_trends(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self.repository.get_orders_summary(filters)

    async def get_inventory_status(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self.repository.get_inventory_summary(filters)

    async def get_warehouse_performance(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        return await self.repository.get_warehouse_metrics(filters)

    async def get_activities(self, limit: int = 20, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self.repository.get_recent_activities(limit, offset, filters)

    async def get_alerts(self, limit: int = 20, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return await self.repository.get_active_alerts(limit, offset, filters)
