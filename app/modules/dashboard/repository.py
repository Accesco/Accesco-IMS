import time
import logging
from typing import List, Dict, Any, Optional, Protocol
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, case

from app.models.order import Order
from app.models.inventory import InventoryItem
from app.models.store import Store
from app.models.audit import AuditLog

logger = logging.getLogger("dashboard.repository")

class DashboardRepositoryProtocol(Protocol):
    async def get_orders_summary(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ...
    async def count_orders(self, filters: Optional[Dict[str, Any]] = None) -> int:
        ...
    async def get_inventory_summary(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ...
    async def get_warehouse_metrics(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        ...
    async def get_revenue_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        ...
    async def get_recent_activities(self, limit: int = 20, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ...
    async def get_active_alerts(self, limit: int = 20, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ...

class DashboardRepository(DashboardRepositoryProtocol):
    def __init__(self, db: AsyncSession):
        self.db = db

    def _apply_filters(self, query: Any, model: Any, filters: Optional[Dict[str, Any]]) -> Any:
        if not filters:
            return query
            
        if filters.get("warehouse_id") and hasattr(model, "store_id"):
            query = query.filter(model.store_id == filters["warehouse_id"])
        
        if hasattr(model, "created_at"):
            if filters.get("from_date"):
                try:
                    fd = datetime.fromisoformat(filters["from_date"])
                    query = query.filter(model.created_at >= fd)
                except ValueError:
                    pass
            if filters.get("to_date"):
                try:
                    td = datetime.fromisoformat(filters["to_date"])
                    query = query.filter(model.created_at <= td)
                except ValueError:
                    pass
                    
        return query

    async def _execute_with_metrics(self, query: Any, name: str) -> Any:
        start_time = time.time()
        result = await self.db.execute(query)
        duration = time.time() - start_time
        logger.info(f"Query {name} executed in {duration:.4f}s")
        return result

    async def get_orders_summary(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query = select(
            func.count(Order.id).label("total"),
            func.sum(case((Order.status == "DELIVERED", 1), else_=0)).label("delivered"),
            func.sum(case((Order.status == "PENDING", 1), else_=0)).label("pending"),
            func.sum(case((Order.status == "CANCELLED", 1), else_=0)).label("cancelled"),
            func.sum(Order.total_amount).label("revenue")
        )
        query = self._apply_filters(query, Order, filters)
        result = await self._execute_with_metrics(query, "get_orders_summary")
        row = result.fetchone()
        
        return {
            "total": row.total or 0,
            "delivered": row.delivered or 0,
            "pending": row.pending or 0,
            "cancelled": row.cancelled or 0,
            "revenue": float(row.revenue or 0)
        }

    async def count_orders(self, filters: Optional[Dict[str, Any]] = None) -> int:
        query = select(func.count(Order.id))
        query = self._apply_filters(query, Order, filters)
        result = await self._execute_with_metrics(query, "count_orders")
        return result.scalar() or 0

    async def get_inventory_summary(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query = select(
            func.sum(InventoryItem.available_quantity).label("available"),
            func.sum(InventoryItem.reserved_quantity).label("reserved"),
            func.sum(case((InventoryItem.available_quantity == 0, 1), else_=0)).label("out_of_stock")
        )
        query = self._apply_filters(query, InventoryItem, filters)
        result = await self._execute_with_metrics(query, "get_inventory_summary")
        row = result.fetchone()
        
        return {
            "available": row.available or 0,
            "reserved": row.reserved or 0,
            "damaged": 0, 
            "out_of_stock": row.out_of_stock or 0
        }

    async def get_warehouse_metrics(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        query = (
            select(
                Store.id.label("store_id"),
                Store.name.label("name"),
                func.count(Order.id).label("orders"),
                func.sum(Order.total_amount).label("revenue")
            )
            .outerjoin(Order, Store.id == Order.store_id)
            .group_by(Store.id)
        )
        
        if filters and filters.get("warehouse_id"):
            query = query.filter(Store.id == filters["warehouse_id"])
            
        result = await self._execute_with_metrics(query, "get_warehouse_metrics")
        rows = result.fetchall()
        
        return [{
            "store_id": row.store_id,
            "name": row.name,
            "orders": row.orders or 0,
            "revenue": float(row.revenue or 0),
            "inventory": 0, 
            "sla": 100.0
        } for row in rows]

    async def get_revenue_data(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        query = select(
            func.date(Order.created_at).label("date"),
            func.sum(Order.total_amount).label("amount")
        ).group_by(func.date(Order.created_at))
        
        query = self._apply_filters(query, Order, filters)
        result = await self._execute_with_metrics(query, "get_revenue_data")
        rows = result.fetchall()
        
        return [{"date": str(r.date), "amount": float(r.amount or 0)} for r in rows]

    async def get_recent_activities(self, limit: int = 20, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        query = select(AuditLog).order_by(AuditLog.created_at.desc())
        query = self._apply_filters(query, AuditLog, filters)
        
        count_query = select(func.count(AuditLog.id))
        count_query = self._apply_filters(count_query, AuditLog, filters)
        total_result = await self._execute_with_metrics(count_query, "get_recent_activities_count")
        total = total_result.scalar() or 0
        
        query = query.limit(limit).offset(offset)
        result = await self._execute_with_metrics(query, "get_recent_activities_items")
        logs = result.scalars().all()
        
        return {
            "items": logs,
            "total": total
        }

    async def get_active_alerts(self, limit: int = 20, offset: int = 0, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {
            "items": [],
            "total": 0
        }
