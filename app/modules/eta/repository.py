from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.eta import ETAPrediction


class ETARepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_prediction(
        self,
        lane_id: str,
        carrier_id: str,
        naive_eta_remaining_min: float,
        predicted_drift_min: float,
        corrected_eta_remaining_min: float,
        current_speed_kmh: float,
        distance_remaining_km: float,
        is_rush_hour: bool,
        shipment_id: Optional[str] = None,
        ml_response_payload: Optional[dict] = None,
    ) -> ETAPrediction:
        prediction = ETAPrediction(
            shipment_id=shipment_id,
            lane_id=lane_id,
            carrier_id=carrier_id,
            naive_eta_remaining_min=naive_eta_remaining_min,
            predicted_drift_min=predicted_drift_min,
            corrected_eta_remaining_min=corrected_eta_remaining_min,
            current_speed_kmh=current_speed_kmh,
            distance_remaining_km=distance_remaining_km,
            is_rush_hour=is_rush_hour,
            ml_response_payload=ml_response_payload,
        )
        self.db.add(prediction)
        await self.db.flush()
        await self.db.refresh(prediction)
        return prediction

    async def get_prediction_by_id(self, prediction_id: int) -> Optional[ETAPrediction]:
        result = await self.db.execute(
            select(ETAPrediction).where(ETAPrediction.id == prediction_id)
        )
        return result.scalar_one_or_none()

    async def get_predictions(
        self,
        shipment_id: Optional[str] = None,
        lane_id: Optional[str] = None,
        carrier_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ETAPrediction]:
        query = select(ETAPrediction)
        if shipment_id is not None:
            query = query.where(ETAPrediction.shipment_id == shipment_id)
        if lane_id is not None:
            query = query.where(ETAPrediction.lane_id == lane_id)
        if carrier_id is not None:
            query = query.where(ETAPrediction.carrier_id == carrier_id)
        query = query.order_by(ETAPrediction.created_at.desc())
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
