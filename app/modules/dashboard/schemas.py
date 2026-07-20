from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel
from typing import List, Optional, TypeVar, Generic
from datetime import datetime

T = TypeVar("T")

class BaseCamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

class StandardResponse(BaseCamelModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: T
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Common Pagination Wrapper
class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

class DashboardFilterParams(BaseModel):
    warehouse_id: Optional[int] = None
    vertical_id: Optional[int] = None
    zone: Optional[str] = None
    carrier: Optional[str] = None
    from_date: Optional[str] = None
    to_date: Optional[str] = None

class DashboardSummaryResponse(BaseCamelModel):
    total_orders: int
    revenue: float
    pending_orders: int
    inventory_accuracy: float
    sla: float
    csat: float
    returns: int
    delivered_orders: int

class RevenueTrend(BaseCamelModel):
    date: str
    amount: float

class RevenueChartResponse(BaseCamelModel):
    daily: List[RevenueTrend]
    weekly: List[RevenueTrend]
    monthly: List[RevenueTrend]
    yearly: List[RevenueTrend]

class OrdersChartResponse(BaseCamelModel):
    created: int
    completed: int
    pending: int
    cancelled: int

class InventoryChartResponse(BaseCamelModel):
    available: int
    reserved: int
    damaged: int
    out_of_stock: int

class WarehousePerformance(BaseCamelModel):
    store_id: int
    name: str
    orders: int
    revenue: float
    inventory: int
    sla: float

class WarehousePerformanceResponse(BaseCamelModel):
    warehouses: List[WarehousePerformance]

class ComplianceResponse(BaseCamelModel):
    audit_score: float
    iso_score: float
    compliance_percent: float
    capa_completion: float

class ActivityItem(BaseCamelModel):
    id: int
    action: str
    module: str
    created_at: datetime
    entity_id: Optional[str] = None

class ActivitiesResponse(BaseCamelModel):
    activities: List[ActivityItem]
    total: int
    page: int
    page_size: int

class AlertItem(BaseCamelModel):
    id: int
    type: str
    message: str
    severity: str
    created_at: datetime

class AlertsResponse(BaseCamelModel):
    alerts: List[AlertItem]
    total: int
    page: int
    page_size: int
