from typing import Optional

from sqlalchemy import String, Float, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class ETAPrediction(Base, TimestampMixin):
    """
    A logged ETA prediction for an in-transit shipment.

    Unlike ReplenishmentRecommendation, this has no approve/reject/
    convert lifecycle -- an ETA prediction isn't a business decision
    to action, it's a point-in-time estimate a dispatcher or customer
    view displays. This table exists as a history log (useful for
    auditing model drift over time, e.g. "was our June ETA accuracy
    worse than July's"), not a workflow state machine.

    lane_id / carrier_id are plain strings, not foreign keys -- there
    are no Lane or Carrier tables in this repo yet (fleet_lanes.py is
    still a synthetic placeholder reference set, see eta-engine/).
    Revisit as a FK once those become real tables.
    """
    __tablename__ = "eta_predictions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    shipment_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    lane_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    carrier_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    naive_eta_remaining_min: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_drift_min: Mapped[float] = mapped_column(Float, nullable=False)
    corrected_eta_remaining_min: Mapped[float] = mapped_column(Float, nullable=False)

    # Telemetry snapshot the prediction was made from, for reproducibility/debugging.
    current_speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    distance_remaining_km: Mapped[float] = mapped_column(Float, nullable=False)
    is_rush_hour: Mapped[bool] = mapped_column(Boolean, nullable=False)

    ml_response_payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
