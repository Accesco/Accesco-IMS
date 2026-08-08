"""
Business logic for the ETA module.

Orchestrates the flow:
    Telemetry Snapshot -> ML Engine -> Persisted Prediction
"""
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException
from app.models.eta import ETAPrediction
from app.modules.eta.repository import ETARepository
from app.modules.eta.ml_client import build_ml_payload, call_ml_engine
from app.modules.eta.schemas import ETAPredictRequest

logger = logging.getLogger(__name__)


class ETAService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ETARepository(db)

    async def predict(self, request: ETAPredictRequest) -> ETAPrediction:
        """
        1. Build the ML payload from the telemetry snapshot
        2. Call the ETA Drift Engine
        3. Persist the prediction (history log, not an actionable
           recommendation -- see app/models/eta.py docstring)
        4. Return the persisted row
        """
        payload = build_ml_payload(
            lane_id=request.lane_id,
            carrier_id=request.carrier_id,
            carrier_on_time_score=request.carrier_on_time_score,
            hour_of_day=request.hour_of_day,
            is_rush_hour=request.is_rush_hour,
            distance_remaining_km=request.distance_remaining_km,
            progress_fraction=request.progress_fraction,
            current_speed_kmh=request.current_speed_kmh,
            avg_speed_so_far_kmh=request.avg_speed_so_far_kmh,
        )

        ml_response = await call_ml_engine(payload)

        prediction = await self.repo.create_prediction(
            shipment_id=request.shipment_id,
            lane_id=request.lane_id,
            carrier_id=request.carrier_id,
            naive_eta_remaining_min=ml_response["naive_eta_remaining_min"],
            predicted_drift_min=ml_response["predicted_drift_min"],
            corrected_eta_remaining_min=ml_response["corrected_eta_remaining_min"],
            current_speed_kmh=request.current_speed_kmh,
            distance_remaining_km=request.distance_remaining_km,
            is_rush_hour=request.is_rush_hour,
            ml_response_payload=ml_response,
        )

        logger.info(
            "ETA prediction created: shipment=%s lane=%s carrier=%s corrected_eta=%.1fmin",
            request.shipment_id, request.lane_id, request.carrier_id,
            ml_response["corrected_eta_remaining_min"],
        )

        await self.db.commit()
        await self.db.refresh(prediction)
        return prediction

    async def get_predictions(
        self,
        shipment_id: Optional[str] = None,
        lane_id: Optional[str] = None,
        carrier_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ETAPrediction]:
        return await self.repo.get_predictions(shipment_id, lane_id, carrier_id, skip, limit)

    async def get_prediction_by_id(self, prediction_id: int) -> ETAPrediction:
        prediction = await self.repo.get_prediction_by_id(prediction_id)
        if not prediction:
            raise ResourceNotFoundException(f"ETA prediction with ID {prediction_id} not found")
        return prediction
