from typing import Optional

from pydantic import BaseModel, Field


class FuelEstimateRequest(BaseModel):
    lane_id: str
    total_weight_kg: float = Field(ge=0.0)
    avg_speed_kmh: Optional[float] = Field(default=None, gt=0.0)
    fuel_price_per_liter: Optional[float] = Field(default=None, gt=0.0)


class FuelEstimateResponse(BaseModel):
    lane_id: str
    distance_km: float
    total_weight_kg: float
    consumption_l_per_100km: float
    liters_consumed: float
    base_l_per_100km: float
    load_penalty_l_per_100km: float
    terrain_penalty_l_per_100km: float
    congestion_penalty_l_per_100km: float
    cost_estimate: Optional[float] = None
