"""
ETAInferenceService
--------------------
Wraps the trained ETA drift model (GradientBoostingRegressor pipeline,
see eta-engine/eta_drift_model.py for training code). Loaded once at
process startup by main.py's lifespan handler -- not per request.
"""

import pandas as pd
import joblib

FEATURE_COLUMNS = [
    "lane_id",
    "carrier_id",
    "carrier_on_time_score",
    "hour_of_day",
    "is_rush_hour",
    "distance_remaining_km",
    "progress_fraction",
    "current_speed_kmh",
    "avg_speed_so_far_kmh",
]

# A stopped truck (red light, loading dock, traffic) legitimately
# reports 0 km/h -- floor it so naive ETA math never divides by ~0.
# Matches MIN_SPEED_KMPH in eta-engine/fleet_telemetry_simulator.py:
# the model was trained on speeds no lower than this floor, so keeping
# them consistent avoids asking it to extrapolate outside that range.
MIN_SPEED_KMPH = 5.0


class ETAInferenceService:
    def __init__(self, model_path: str):
        self.pipeline = joblib.load(model_path)
        self.expected_features = FEATURE_COLUMNS

    def predict(self, request) -> dict:
        safe_speed = max(request.current_speed_kmh, MIN_SPEED_KMPH)
        naive_eta_remaining_min = (request.distance_remaining_km / safe_speed) * 60.0

        row = pd.DataFrame([{
            "lane_id": request.lane_id,
            "carrier_id": request.carrier_id,
            "carrier_on_time_score": request.carrier_on_time_score,
            "hour_of_day": request.hour_of_day,
            "is_rush_hour": request.is_rush_hour,
            "distance_remaining_km": request.distance_remaining_km,
            "progress_fraction": request.progress_fraction,
            "current_speed_kmh": request.current_speed_kmh,
            "avg_speed_so_far_kmh": request.avg_speed_so_far_kmh,
        }])

        predicted_drift_min = float(self.pipeline.predict(row)[0])
        corrected_eta_remaining_min = naive_eta_remaining_min + predicted_drift_min

        return {
            "naive_eta_remaining_min": round(naive_eta_remaining_min, 2),
            "predicted_drift_min": round(predicted_drift_min, 2),
            "corrected_eta_remaining_min": round(corrected_eta_remaining_min, 2),
        }
