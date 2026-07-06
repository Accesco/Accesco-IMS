# Predictive Replenishment Engine — Inference API
**Accesco Living | Version: 0.3.0**

REST API exposing the XGBoost replenishment classifier for consumption by the IMS.

---

## Folder Structure

```
replenishment-api/
├── main.py                          # FastAPI app entrypoint, route definitions
├── inference.py                     # Model loading and prediction logic
├── schemas.py                       # Pydantic request/response schemas
├── predictive_replenishment_model.pkl  # Model artifact (place here before running)
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
└── tests/
    ├── test_api.py                  # End-to-end API tests (via TestClient)
    └── test_inference.py            # Unit tests for inference service in isolation
```

---

## Setup & Running

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Place the model artifact
```bash
# Copy the pkl file into this folder
cp path/to/predictive_replenishment_model.pkl .
```

### 3. Start the server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The interactive API docs (Swagger UI) are available at:
`http://localhost:8000/docs`

### 4. Custom model path (optional)
```bash
MODEL_PATH=/path/to/model.pkl uvicorn main:app --host 0.0.0.0 --port 8000
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
    "On_Hand", "Reserved", "Daily_Velocity",
    "Dark_Store_ID_DS-BLR-01", "Dark_Store_ID_DS-BLR-02", "Dark_Store_ID_DS-BLR-03",
    "Temp_Zone_Ambient", "Temp_Zone_Chilled", "Temp_Zone_Frozen"
  ]
}
```

---

### `POST /predict-replenishment`

Accepts SKU-level inventory telemetry and returns an urgent reorder prediction.

**Request schema:**

| Field            | Type    | Required | Constraints                                      | Description                          |
|------------------|---------|----------|--------------------------------------------------|--------------------------------------|
| `sku_id`         | string  | ✅       | —                                                | SKU identifier                       |
| `store_id`       | string  | ✅       | One of: DS-BLR-01, DS-BLR-02, DS-BLR-03         | Dark store location                  |
| `on_hand`        | integer | ✅       | >= 0                                             | Total physical units in store        |
| `reserved`       | integer | ✅       | >= 0                                             | Units held for pending orders        |
| `daily_velocity` | float   | ✅       | > 0                                              | Average units sold per day           |
| `temp_zone`      | string  | ✅       | One of: Ambient, Chilled, Frozen                 | Storage temperature zone             |

> **Note:** `available` and `reorder_level` are intentionally absent.
> Both are direct arithmetic derivations of the target label — including them causes data leakage.

**Sample request — low stock (Tata Tea Premium at DS-BLR-01):**
```json
{
  "sku_id": "ACS-45566",
  "store_id": "DS-BLR-01",
  "on_hand": 1,
  "reserved": 0,
  "daily_velocity": 10.0,
  "temp_zone": "Ambient"
}
```

**Sample response — urgent reorder:**
```json
{
  "sku_id": "ACS-45566",
  "store_id": "DS-BLR-01",
  "urgent_reorder": true,
  "confidence_score": 0.9928,
  "action": "GENERATE_PURCHASE_ORDER"
}
```

---

**Sample request — healthy stock (Parle-G Biscuits at DS-BLR-01):**
```json
{
  "sku_id": "ACS-99682",
  "store_id": "DS-BLR-01",
  "on_hand": 117,
  "reserved": 11,
  "daily_velocity": 14.32,
  "temp_zone": "Ambient"
}
```

**Sample response — no action:**
```json
{
  "sku_id": "ACS-99682",
  "store_id": "DS-BLR-01",
  "urgent_reorder": false,
  "confidence_score": 0.0312,
  "action": "NO_ACTION_REQUIRED"
}
```

---

**Validation error (422):**
```json
{
  "detail": [
    {
      "type": "literal_error",
      "loc": ["body", "store_id"],
      "msg": "Input should be 'DS-BLR-01', 'DS-BLR-02' or 'DS-BLR-03'",
      "input": "DS-MUM-99"
    }
  ]
}
```

---

## Running Tests

```bash
# From the replenishment-api/ directory
pytest tests/ -v
```

Expected output:
```
tests/test_api.py::test_health_check                          PASSED
tests/test_api.py::test_low_stock_returns_urgent_reorder      PASSED
tests/test_api.py::test_healthy_stock_returns_no_action       PASSED
tests/test_api.py::test_response_contains_all_required_fields PASSED
...
tests/test_inference.py::test_feature_row_has_correct_column_count  PASSED
tests/test_inference.py::test_store_id_one_hot_encoding_ds_blr_01   PASSED
...
```

---

## Design Notes

**Model loaded once at startup** — via FastAPI's `lifespan` context manager, the `.pkl` artifact is loaded into memory when the server starts, not on each request. This follows the same pattern as the existing IMS workers.

**Schema-tolerant inference** — feature rows are built with `reindex()` against the model's stored feature list, so payload evolution doesn't cause `ValueError` mismatches.

**Clean string API** — callers pass `store_id: "DS-BLR-01"` and `temp_zone: "Ambient"` as plain strings. One-hot encoding happens internally in `inference.py`, invisible to the IMS consumer.

**No leaky features** — `available` and `reorder_level` are not accepted as inputs. The model was trained without them to prevent data leakage.
