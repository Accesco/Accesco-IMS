from fastapi import HTTPException

from app.modules.fuel.fuel_engine import estimate_fuel
from app.modules.fuel.schemas import FuelEstimateRequest, FuelEstimateResponse


class FuelEstimationService:
    """Stateless -- computes and returns an estimate, nothing persisted."""

    def estimate(self, request: FuelEstimateRequest) -> FuelEstimateResponse:
        try:
            result = estimate_fuel(
                lane_id=request.lane_id,
                total_weight_kg=request.total_weight_kg,
                avg_speed_kmh=request.avg_speed_kmh,
                fuel_price_per_liter=request.fuel_price_per_liter,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

        return FuelEstimateResponse(
            lane_id=result.lane_id,
            distance_km=result.distance_km,
            total_weight_kg=result.total_weight_kg,
            consumption_l_per_100km=result.consumption_l_per_100km,
            liters_consumed=result.liters_consumed,
            base_l_per_100km=result.base_l_per_100km,
            load_penalty_l_per_100km=result.load_penalty_l_per_100km,
            terrain_penalty_l_per_100km=result.terrain_penalty_l_per_100km,
            congestion_penalty_l_per_100km=result.congestion_penalty_l_per_100km,
            cost_estimate=result.cost_estimate,
        )
