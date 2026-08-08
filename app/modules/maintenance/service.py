from app.modules.maintenance.ml_client import build_ml_payload, call_ml_engine
from app.modules.maintenance.schemas import MaintenancePredictRequest, MaintenancePredictResponse


class MaintenanceService:
    """Stateless -- calls the ML engine and returns the result.
    Nothing persisted (see chat: same decision as app/modules/loads)."""

    async def predict(self, request: MaintenancePredictRequest) -> MaintenancePredictResponse:
        payload = build_ml_payload(
            lane_id=request.lane_id,
            terrain_factor=request.terrain_factor,
            vehicle_age_years=request.vehicle_age_years,
            km_since_last_service=request.km_since_last_service,
            days_since_last_service=request.days_since_last_service,
            avg_daily_km_this_interval=request.avg_daily_km_this_interval,
            avg_load_utilization_pct=request.avg_load_utilization_pct,
            harsh_events_per_1000km=request.harsh_events_per_1000km,
        )

        ml_response = await call_ml_engine(payload)

        return MaintenancePredictResponse(
            vehicle_id=request.vehicle_id,
            naive_km_remaining=ml_response["naive_km_remaining"],
            predicted_drift_km=ml_response["predicted_drift_km"],
            corrected_km_remaining=ml_response["corrected_km_remaining"],
        )
