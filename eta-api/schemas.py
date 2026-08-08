from typing import List, Optional

from pydantic import BaseModel, Field


class ETARequest(BaseModel):
    """A single telemetry snapshot -- what a real carrier telematics
    ping provides (blueprint section 4B), joined with static lane/
    carrier reference data by the caller (the IMS ml_client)."""
    lane_id: str
    carrier_id: str
    carrier_on_time_score: float = Field(ge=0.0, le=1.0)
    hour_of_day: float = Field(ge=0.0, lt=24.0)
    is_rush_hour: bool
    distance_remaining_km: float = Field(ge=0.0)
    progress_fraction: float = Field(ge=0.0, le=1.0)
    current_speed_kmh: float = Field(ge=0.0)
    avg_speed_so_far_kmh: float = Field(ge=0.0)


class ETAResponse(BaseModel):
    naive_eta_remaining_min: float
    predicted_drift_min: float
    corrected_eta_remaining_min: float


class HealthResponse(BaseModel):
    status: str
    model_features: Optional[List[str]] = None
