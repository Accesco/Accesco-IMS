# ETA Drift Engine
**Accesco Living — TMS ETA Prediction**
**Version:** 0.1 | **Date:** August 2026

---

## What This Does

A machine learning pipeline that predicts a corrected ETA for in-transit
truck shipments. Rather than just recomputing `distance_remaining /
current_speed`, it predicts the **drift** between that naive estimate
and the actual remaining time, using signals available at telemetry-ping
time: lane, carrier, time of day, current/average speed.

This matches the "ML ETA Drift" concept in the TMS blueprint's Tracking
Layer -- a naive ETA is a systematically biased estimator (e.g. during a
temporary rush-hour slowdown it wildly overestimates remaining time,
since it assumes the current crawl continues for the whole trip). The
drift model learns and corrects for these patterns.

---

## Folder Structure

```
eta-engine/
│
├── fleet_lanes.py                  # Synthetic lane/carrier reference data
├── fleet_telemetry_simulator.py    # Simulates truck telemetry (no real data yet)
├── eta_drift_model.py              # Trains + evaluates the drift model
├── eta_drift_model.joblib          # Serialized sklearn pipeline artifact
├── README.md                       # This file
```

---

## How to Run

### 1. Generate synthetic telemetry data
```bash
python fleet_telemetry_simulator.py --n-shipments 400 --seed 42
```
Simulates full truck trips (so the true outcome is known), then emits
telemetry snapshots along the way -- exactly how you'd derive training
labels from a history of completed real trips.

### 2. Train the model
```bash
python eta_drift_model.py --data fleet_telemetry.csv
```
Trains a GradientBoostingRegressor, evaluates on **held-out shipments**
(not held-out rows -- a shipment's ticks are correlated, so row-level
splitting would leak a truck's own trip across train/test), and saves
`eta_drift_model.joblib`.

### 3. Serve it
See `../eta-api/` for the FastAPI inference service that loads this
artifact and exposes `POST /predict-eta`.

---

## Model Details

| Parameter | Value |
|---|---|
| Algorithm | GradientBoostingRegressor (scikit-learn) |
| `n_estimators` | 300 |
| `max_depth` | 4 |
| `learning_rate` | 0.05 |
| Train / Test split | 75 / 25, grouped by shipment_id |
| Target | `drift_min` (actual_remaining_min − naive_eta_remaining_min) |
| Artifact | `eta_drift_model.joblib` |

**Features used at inference:** `lane_id`, `carrier_id` (one-hot),
`carrier_on_time_score`, `hour_of_day`, `is_rush_hour`,
`distance_remaining_km`, `progress_fraction`, `current_speed_kmh`,
`avg_speed_so_far_kmh`

**Evaluation result:** ~60-63% MAE reduction vs. naive ETA, consistent
across multiple train/test splits (naive ~40-46 min avg error →
model-corrected ~16-17 min). Feature importance: `current_speed_kmh`
(52%) and `distance_remaining_km` (29%) dominate, which lines up with
how the simulated speed effects were designed.

---

## Known Limitations

| Limitation | Planned Fix |
|---|---|
| Synthetic training data (placeholder lanes/carriers) | Replace with real historical trip + telemetry logs |
| No true "stopped truck" (0 km/h) scenarios in training | Add explicit stop/dwell events to the simulator, not just partial slowdowns |
| Speed floor (5 km/h) doesn't reflect genuinely idle time | Model dwell time (loading docks, mandatory rest breaks) as a distinct feature |
| No confidence/uncertainty estimate returned | Add prediction interval (e.g. quantile regression) so low-confidence corrections are flagged |
| Single-region synthetic lane set | Extend to real facility network once available |

---

## Dependencies

```
pandas
numpy
scikit-learn
joblib
```

---

## Contact

Built as part of the Accesco Living TMS rider/fleet workstream.
