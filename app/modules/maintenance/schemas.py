from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class MaintenancePredictRequest(BaseModel):
    vehicle_id: str
    lane_id: str
    terrain_factor: float = Field(ge=0.0, le=1.0)
    vehicle_age_years: float = Field(ge=0.0)
    km_since_last_service: float = Field(ge=0.0)
    days_since_last_service: int = Field(ge=0)
    avg_daily_km_this_interval: float = Field(ge=0.0)
    avg_load_utilization_pct: float = Field(ge=0.0, le=100.0)
    harsh_events_per_1000km: float = Field(ge=0.0)


class MaintenancePredictResponse(BaseModel):
    vehicle_id: str
    naive_km_remaining: float
    predicted_drift_km: float
    corrected_km_remaining: float

    model_config = ConfigDict(from_attributes=True)


