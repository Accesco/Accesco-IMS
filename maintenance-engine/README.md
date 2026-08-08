# Maintenance Drift Engine
**Accesco Living — TMS Vehicle Maintenance Prediction**
**Version:** 0.1 | **Date:** August 2026

---

## What This Does

Predicts a corrected estimate of remaining distance until a vehicle's
next maintenance is genuinely due, correcting a naive fixed-interval
rule ("every 10,000 km") using real usage-pattern signals: average
load carried, driving harshness (harsh braking/acceleration events),
terrain, and vehicle age.

A naive fixed-interval rule treats every vehicle identically regardless
of how hard it's actually being used -- a heavily-loaded truck running
harsh mountain routes wears out meaningfully faster than a lightly-
loaded one on flat highway, but a naive rule schedules both for service
at the same 10,000 km mark. This model learns and corrects for that gap.

---

## Folder Structure

```
maintenance-engine/
│
├── vehicle_usage_simulator.py      # Simulates fleet usage + wear accumulation
├── maintenance_model.py            # Trains + evaluates the drift model
├── maintenance_drift_model.joblib  # Serialized sklearn pipeline artifact
├── README.md                       # This file
```

---

## How to Run

### 1. Generate synthetic usage data
```bash
python vehicle_usage_simulator.py --n-vehicles 150 --seed 42
```
Simulates ~2 years of daily usage per vehicle, tracking both physical
km driven and wear-adjusted km (which accumulates faster than physical
distance under heavy load / harsh driving / hilly terrain / vehicle
age). Emits one training snapshot per vehicle-day, with ground truth
backfilled once each service interval closes.

### 2. Train the model
```bash
python maintenance_model.py --data vehicle_usage.csv
```
Trains a GradientBoostingRegressor, evaluates on **held-out vehicles**
(not held-out rows -- a vehicle's snapshots are highly correlated, so
row-level splitting would leak a vehicle's own usage pattern across
train/test), saves `maintenance_drift_model.joblib`.

### 3. Serve it
See `../maintenance-api/` for the FastAPI inference service.

---

## Model Details

| Parameter | Value |
|---|---|
| Algorithm | GradientBoostingRegressor (scikit-learn) |
| Train / Test split | 75 / 25, grouped by vehicle_id |
| Target | `drift_km` (actual_km_remaining − naive_km_remaining) |
| Artifact | `maintenance_drift_model.joblib` |

**Evaluation result:** ~94-95% MAE reduction vs. naive fixed-interval
baseline, consistent across multiple train/test splits (naive ~3,000-
3,200 km avg error → model-corrected ~165-180 km).

**Feature importance:** `terrain_factor` (39%) and
`harsh_events_per_1000km` (31%) dominate -- both have the largest
coefficients in the underlying wear-accumulation formula, so this is
expected and consistent with how the simulation was designed, not an
artifact.

---

## Known Limitations

| Limitation | Planned Fix |
|---|---|
| Synthetic wear model, not real maintenance/failure logs | Replace with real fleet service-history data once available |
| Near-perfect fit (94-95%) reflects a deterministic synthetic formula the model can closely reverse-engineer, since it has the exact features that generated the label | Expect materially more modest gains on noisy real-world data with unmeasured failure causes |
| `avg_load_utilization_pct` has near-zero learned importance (0.0075) despite a real coefficient in the wear formula, because load is resampled i.i.d. per day rather than being a persistent per-vehicle trait | Model load as a vehicle-level tendency (e.g. "usually runs heavy freight") if real fleets show this pattern, not just daily noise |
| No true mechanical-failure events (only gradual wear) | Add discrete failure-event modeling (e.g. component-level survival analysis) for a more complete picture |
| Single synthetic lane network shared conceptually with eta-engine, but re-declared locally here to avoid a cross-service dependency | Point both at a shared lanes reference once real facility/lane data exists |

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
