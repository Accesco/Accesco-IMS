"""
ETAInferenceService
--------------------
Wraps the trained ETA drift model (GradientBoostingRegressor pipeline,
see eta-engine/eta_drift_model.py for training code). Loaded once at
process startup by main.py's lifespan handler -- not per request.
"""

from pathlib import Path

import pandas as pd
import joblib


class FallbackETAModel:
    """Deterministic fallback used when the trained joblib asset is unavailable."""

    def predict(self, row: pd.DataFrame) -> list[float]:
        predictions = []
        for _, values in row.iterrows():
            distance = float(values.get("distance_remaining_km", 0.0))
            speed = max(float(values.get("current_speed_kmh", 0.0)), 5.0)
            progress = float(values.get("progress_fraction", 0.0))
            lane = str(values.get("lane_id", ""))
            carrier = str(values.get("carrier_id", ""))
            rush = bool(values.get("is_rush_hour", False))
            on_time = float(values.get("carrier_on_time_score", 0.0))
            hour = float(values.get("hour_of_day", 0.0))
            avg_speed = float(values.get("avg_speed_so_far_kmh", 0.0))

            drift = 0.0
            if lane:
                drift += 2.0 if "BLR" in lane else 0.5
            if carrier:
                drift += 1.0 if "CARR" in carrier else 0.0
            drift += (0.3 if rush else -0.1) * 10.0
            drift += (on_time - 0.5) * 15.0
            drift += (hour - 12.0) * 0.2
            drift += max(0.0, (avg_speed - speed) * 0.1)
            drift += (progress - 0.5) * 5.0
            drift += (distance / max(speed, 1.0)) * 0.01
            predictions.append(drift)
        return predictions

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
        candidate = Path(model_path)
        if not candidate.is_absolute():
            candidate = Path(__file__).resolve().parent / candidate

        if candidate.exists():
            try:
                self.pipeline = joblib.load(candidate)
            except Exception:
                self.pipeline = FallbackETAModel()
        else:
            self.pipeline = FallbackETAModel()

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
