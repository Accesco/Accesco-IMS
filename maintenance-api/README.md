# Maintenance Drift Engine — Inference API
**Accesco Living | Author: Amit Kumar Singh | Version: 0.1.0**

REST API exposing the GradientBoosting maintenance drift model for consumption by the IMS.

---

## Folder Structure

```
maintenance-api/
├── main.py                          # FastAPI app entrypoint, route definitions
├── inference.py                     # Model loading and prediction logic
├── schemas.py                       # Pydantic request/response schemas
├── maintenance_drift_model.joblib   # Model artifact (place here before running)
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
└── tests/
    ├── conftest.py                  # sys.path setup (isolated from sibling services -- see Design Notes)
    └── test_maintenance_api.py      # End-to-end API tests (via TestClient)
```

---

## Setup & Running

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Place the model artifact
```bash
# Copy the joblib file into this folder
cp path/to/maintenance_drift_model.joblib .
```

### 3. Start the server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8002
```

The interactive API docs (Swagger UI) are available at:
`http://localhost:8002/docs`

### 4. Custom model path (optional)
```bash
MODEL_PATH=/path/to/model.joblib uvicorn main:app --host 0.0.0.0 --port 8002
```

---

## API Reference

### `GET /health`

Returns service status and the model's loaded feature schema.

**Response:**
```json
{
  "status": "ok",
  "model_features": [
    "lane_id", "terrain_factor", "vehicle_age_years",
    "km_since_last_service", "days_since_last_service",
    "avg_daily_km_this_interval", "avg_load_utilization_pct",
    "harsh_events_per_1000km"
  ]
}
```

---

### `POST /predict-maintenance`

Accepts a vehicle usage snapshot and returns a corrected estimate of
remaining distance until maintenance is genuinely due.

**Request schema:**

| Field                          | Type    | Required | Constraints   | Description                                        |
|---------------------------------|---------|----------|---------------|------------------------------------------------------|
| `lane_id`                      | string  | ✅       | —             | Vehicle's primary lane/route                         |
| `terrain_factor`                | float   | ✅       | 0.0 – 1.0     | 0 = flat/fast lane, 1 = hilliest lane in the network |
| `vehicle_age_years`             | float   | ✅       | >= 0          | Vehicle age                                          |
| `km_since_last_service`         | float   | ✅       | >= 0          | Physical distance since last service                 |
| `days_since_last_service`       | integer | ✅       | >= 0          | Calendar days since last service                      |
| `avg_daily_km_this_interval`    | float   | ✅       | >= 0          | Average daily distance this service interval          |
| `avg_load_utilization_pct`      | float   | ✅       | 0.0 – 100.0   | Average % of max load capacity carried               |
| `harsh_events_per_1000km`       | float   | ✅       | >= 0          | Hard braking/acceleration events per 1,000 km         |

**Sample request — heavy use (hilly terrain, harsh driving, older vehicle):**
```json
{
  "lane_id": "LANE-BLR-MAA",
  "terrain_factor": 1.0,
  "vehicle_age_years": 6.0,
  "km_since_last_service": 4000.0,
  "days_since_last_service": 90,
  "avg_daily_km_this_interval": 400.0,
  "avg_load_utilization_pct": 80.0,
  "harsh_events_per_1000km": 12.0
}
```

**Sample response — service due much sooner than the naive rule suggests:**
```json
{
  "naive_km_remaining": 6000.0,
  "predicted_drift_km": -4682.7,
  "corrected_km_remaining": 1317.3
}
```

---

**Sample request — gentle use (flat terrain, gentle driving, newer vehicle):**
```json
{
  "lane_id": "LANE-BLR-PUN",
  "terrain_factor": 0.0,
  "vehicle_age_years": 1.0,
  "km_since_last_service": 4000.0,
  "days_since_last_service": 15,
  "avg_daily_km_this_interval": 300.0,
  "avg_load_utilization_pct": 40.0,
  "harsh_events_per_1000km": 1.0
}
```

**Sample response — smaller correction, closer to the naive estimate:**
```json
{
  "naive_km_remaining": 6000.0,
  "predicted_drift_km": -1946.6,
  "corrected_km_remaining": 4053.4
}
```

---

**Validation error (422):**
```json
{
  "detail": [
    {
      "type": "less_than_equal",
      "loc": ["body", "avg_load_utilization_pct"],
      "msg": "Input should be less than or equal to 100",
      "input": 150.0
    }
  ]
}
```

---

## Running Tests

```bash
# From the maintenance-api/ directory
pytest tests/ -v
```

Expected output:
```
tests/test_maintenance_api.py::test_health_check                                  PASSED
tests/test_maintenance_api.py::test_valid_request_returns_200                     PASSED
tests/test_maintenance_api.py::test_corrected_equals_naive_plus_drift             PASSED
tests/test_maintenance_api.py::test_naive_km_remaining_matches_fixed_interval_formula  PASSED
tests/test_maintenance_api.py::test_heavy_use_gets_bigger_correction_than_gentle_use   PASSED
tests/test_maintenance_api.py::test_missing_required_field_returns_422            PASSED
tests/test_maintenance_api.py::test_negative_km_since_service_returns_422         PASSED
tests/test_maintenance_api.py::test_out_of_range_terrain_factor_returns_422       PASSED
tests/test_maintenance_api.py::test_out_of_range_load_utilization_returns_422     PASSED
tests/test_maintenance_api.py::test_empty_body_returns_422                        PASSED
tests/test_maintenance_api.py::test_model_loaded_once_on_startup                  PASSED
```

---

## Design Notes

**Model loaded once at startup** — via FastAPI's `lifespan` context manager, the `.joblib` artifact is loaded into memory when the server starts, not on each request. Same pattern as `replenishment-api` and `eta-api`.

**Drift-correction framing, not a raw prediction** — the model predicts the gap between a naive fixed-interval rule ("every 10,000 km") and the actual remaining distance, rather than predicting remaining distance directly. This keeps the naive baseline visible in the response (`naive_km_remaining`) alongside the correction, so a caller can see exactly how much the model is adjusting and why, rather than trusting an opaque number.

**Stopped/zero-usage inputs are safe** — there's no divide-by-zero risk in this service the way there was in `eta-api` (no speed-based ratio here), but all numeric fields still carry explicit `Field` bounds so malformed telemetry fails fast with a 422, not a silent bad prediction.

**Test file naming** — `test_maintenance_api.py` (not `test_api.py`) is deliberate: `eta-api` and `replenishment-api` both originally used the generic name `test_api.py`, which caused a pytest "import file mismatch" collection error the first time both services' tests were collected in one combined CI run (see repo history / CI incident). Using a unique basename here is a small, cheap defense against that same class of bug recurring with a third service in the mix, on top of the CI fix that isolates each service's test run.

**Known caveat on the model itself** — this is trained entirely on synthetic usage data (`maintenance-engine/README.md` has the full writeup), including a caveat that its current ~94-95% MAE improvement over the naive baseline is inflated by the synthetic wear formula being deterministic. Treat this as a proof of concept for the drift-correction approach, not a production-accuracy claim, until retrained on real fleet service-history data.
