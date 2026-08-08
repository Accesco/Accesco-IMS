from typing import List, Optional

from pydantic import BaseModel, Field


class MaintenanceRequest(BaseModel):
    """A vehicle usage snapshot -- what a fleet telematics/odometer
    system would provide at any point in a service interval."""
    lane_id: str
    terrain_factor: float = Field(ge=0.0, le=1.0)
    vehicle_age_years: float = Field(ge=0.0)
    km_since_last_service: float = Field(ge=0.0)
    days_since_last_service: int = Field(ge=0)
    avg_daily_km_this_interval: float = Field(ge=0.0)
    avg_load_utilization_pct: float = Field(ge=0.0, le=100.0)
    harsh_events_per_1000km: float = Field(ge=0.0)


class MaintenanceResponse(BaseModel):
    naive_km_remaining: float
    predicted_drift_km: float
    corrected_km_remaining: float


class HealthResponse(BaseModel):
    status: str
    model_features: Optional[List[str]] = None
