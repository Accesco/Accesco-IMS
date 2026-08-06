from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# --- Request Schemas ---

class ETAPredictRequest(BaseModel):
    """A single telemetry snapshot -- what a real carrier telematics
    ping provides (blueprint section 4B)."""
    shipment_id: Optional[str] = None
    lane_id: str
    carrier_id: str
    carrier_on_time_score: float = Field(ge=0.0, le=1.0)
    hour_of_day: float = Field(ge=0.0, lt=24.0)
    is_rush_hour: bool
    distance_remaining_km: float = Field(ge=0.0)
    progress_fraction: float = Field(ge=0.0, le=1.0)
    current_speed_kmh: float = Field(ge=0.0)
    avg_speed_so_far_kmh: float = Field(ge=0.0)


# --- Response Schemas ---

class ETAPredictionResponse(BaseModel):
    """A single persisted ETA prediction, as stored in the database."""
    id: int
    shipment_id: Optional[str] = None
    lane_id: str
    carrier_id: str
    naive_eta_remaining_min: float
    predicted_drift_min: float
    corrected_eta_remaining_min: float
    current_speed_kmh: float
    distance_remaining_km: float
    is_rush_hour: bool
    ml_response_payload: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ETAPredictionListResponse(BaseModel):
    predictions: List[ETAPredictionResponse]
    count: int
