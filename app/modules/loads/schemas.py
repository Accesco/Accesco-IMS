from typing import List, Optional

from pydantic import BaseModel, Field


class ERPOrderInput(BaseModel):
    """A single order to be consolidated onto a truck. Matches the
    blueprint's ERP Orders Record (section 2A): reference, physical
    attributes (weight/volume), lane, and delivery deadline."""
    order_ref: str
    lane_id: str
    weight_kg: float = Field(gt=0.0)
    volume_cbm: float = Field(gt=0.0)
    deadline_hour: float = Field(ge=0.0)


class ConsolidationRequest(BaseModel):
    orders: List[ERPOrderInput] = Field(min_length=1)


class TruckLoadResponse(BaseModel):
    truck_id: str
    lane_id: str
    n_orders: int
    total_weight_kg: float
    total_volume_cbm: float
    weight_utilization_pct: float
    volume_utilization_pct: float
    binding_constraint: str
    order_refs_by_deadline: List[str]


class ConsolidationSummary(BaseModel):
    n_orders_input: int
    n_orders_packed: int
    n_oversized_orders: int
    n_trucks: int
    avg_weight_utilization_pct: Optional[float] = None
    avg_volume_utilization_pct: Optional[float] = None
    trucks_binding_on_weight: int = 0
    trucks_binding_on_volume: int = 0


class ConsolidationResponse(BaseModel):
    summary: ConsolidationSummary
    loads: List[TruckLoadResponse]
    oversized_order_refs: List[str]
