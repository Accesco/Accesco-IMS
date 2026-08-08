"""
predict_eta.py
---------------
Inference-time usage of the trained ETA drift model: given a single
telemetry snapshot (what a real system would have at that moment),
returns a corrected ETA.

Usage as a library:
    from predict_eta import predict_eta
    minutes_remaining = predict_eta(
        lane_id="LANE-BLR-HYD", carrier_id="CARR-004", carrier_on_time_score=0.82,
        hour_of_day=8.5, is_rush_hour=True, distance_remaining_km=410.0,
        progress_fraction=0.18, current_speed_kmh=32.0, avg_speed_so_far_kmh=48.0,
    )

Usage as a script: runs a few illustrative example predictions.
"""

import os

import joblib
import pandas as pd

_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eta_drift_model.joblib")
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = joblib.load(_MODEL_PATH)
    return _model


def predict_eta(lane_id, carrier_id, carrier_on_time_score, hour_of_day, is_rush_hour,
                 distance_remaining_km, progress_fraction, current_speed_kmh,
                 avg_speed_so_far_kmh):
    """
    Returns (naive_eta_remaining_min, predicted_drift_min, corrected_eta_remaining_min).
    """
    naive_eta_remaining_min = (distance_remaining_km / current_speed_kmh) * 60.0

    row = pd.DataFrame([{
        "lane_id": lane_id,
        "carrier_id": carrier_id,
        "carrier_on_time_score": carrier_on_time_score,
        "hour_of_day": hour_of_day,
        "is_rush_hour": is_rush_hour,
        "distance_remaining_km": distance_remaining_km,
        "progress_fraction": progress_fraction,
        "current_speed_kmh": current_speed_kmh,
        "avg_speed_so_far_kmh": avg_speed_so_far_kmh,
    }])

    model = _get_model()
    predicted_drift_min = float(model.predict(row)[0])
    corrected_eta_remaining_min = naive_eta_remaining_min + predicted_drift_min

    return naive_eta_remaining_min, predicted_drift_min, corrected_eta_remaining_min


def main():
    examples = [
        dict(
            label="Truck stuck in morning rush, still far from destination",
            lane_id="LANE-BLR-HYD", carrier_id="CARR-004", carrier_on_time_score=0.82,
            hour_of_day=8.5, is_rush_hour=True, distance_remaining_km=410.0,
            progress_fraction=0.18, current_speed_kmh=32.0, avg_speed_so_far_kmh=48.0,
        ),
        dict(
            label="Same truck, but now on open highway mid-trip, no rush hour",
            lane_id="LANE-BLR-HYD", carrier_id="CARR-004", carrier_on_time_score=0.82,
            hour_of_day=13.0, is_rush_hour=False, distance_remaining_km=250.0,
            progress_fraction=0.56, current_speed_kmh=72.0, avg_speed_so_far_kmh=58.0,
        ),
        dict(
            label="High-scoring carrier, nearly arrived, evening rush near destination",
            lane_id="LANE-BLR-CHN", carrier_id="CARR-006", carrier_on_time_score=0.95,
            hour_of_day=18.5, is_rush_hour=True, distance_remaining_km=25.0,
            progress_fraction=0.93, current_speed_kmh=28.0, avg_speed_so_far_kmh=62.0,
        ),
    ]

    for ex in examples:
        label = ex.pop("label")
        naive, drift, corrected = predict_eta(**ex)
        print(f"{label}")
        print(f"  naive ETA remaining:     {naive:7.1f} min")
        print(f"  model drift correction:  {drift:+7.1f} min")
        print(f"  corrected ETA remaining: {corrected:7.1f} min\n")


if __name__ == "__main__":
    main()
