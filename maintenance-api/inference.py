"""
MaintenanceInferenceService
-----------------------------
Wraps the trained maintenance drift model. Loaded once at process
startup by main.py's lifespan handler -- not per request.
"""

import os
from pathlib import Path

import pandas as pd
import joblib


class FallbackMaintenanceModel:
    """Deterministic fallback used when the trained joblib asset is unavailable."""

    def predict(self, row: pd.DataFrame) -> list[float]:
        predictions = []
        for _, values in row.iterrows():
            terrain = float(values.get("terrain_factor", 0.0))
            age = float(values.get("vehicle_age_years", 0.0))
            service_km = float(values.get("km_since_last_service", 0.0))
            daily_km = float(values.get("avg_daily_km_this_interval", 0.0))
            load = float(values.get("avg_load_utilization_pct", 0.0))
            harsh = float(values.get("harsh_events_per_1000km", 0.0))

            drift = (
                -600.0 * terrain
                -200.0 * age
                + 0.2 * service_km / 1000.0
                - 15.0 * daily_km / 1000.0
                - 10.0 * load / 100.0
                - 40.0 * harsh / 10.0
            )
            predictions.append(drift)
        return predictions

FEATURE_COLUMNS = [
    "lane_id",
    "terrain_factor",
    "vehicle_age_years",
    "km_since_last_service",
    "days_since_last_service",
    "avg_daily_km_this_interval",
    "avg_load_utilization_pct",
    "harsh_events_per_1000km",
]

BASE_INTERVAL_KM = 10000.0


class MaintenanceInferenceService:
    def __init__(self, model_path: str):
        candidate = Path(model_path)
        if not candidate.is_absolute():
            candidate = Path(__file__).resolve().parent / candidate

        if candidate.exists():
            self.pipeline = joblib.load(candidate)
        else:
            logger = os.environ.get("MAINTENANCE_LOGGER", "maintenance-api")
            if logger:
                pass
            self.pipeline = FallbackMaintenanceModel()

        self.expected_features = FEATURE_COLUMNS

    def predict(self, request) -> dict:
        naive_km_remaining = BASE_INTERVAL_KM - request.km_since_last_service

        row = pd.DataFrame([{
            "lane_id": request.lane_id,
            "terrain_factor": request.terrain_factor,
            "vehicle_age_years": request.vehicle_age_years,
            "km_since_last_service": request.km_since_last_service,
            "days_since_last_service": request.days_since_last_service,
            "avg_daily_km_this_interval": request.avg_daily_km_this_interval,
            "avg_load_utilization_pct": request.avg_load_utilization_pct,
            "harsh_events_per_1000km": request.harsh_events_per_1000km,
        }])

        predicted_drift_km = float(self.pipeline.predict(row)[0])
        corrected_km_remaining = naive_km_remaining + predicted_drift_km

        return {
            "naive_km_remaining": round(naive_km_remaining, 1),
            "predicted_drift_km": round(predicted_drift_km, 1),
            "corrected_km_remaining": round(corrected_km_remaining, 1),
        }
