# Predictive Replenishment Engine
**Assesco Living — Dark Store Inventory Intelligence**
**Version:** 0.2 | **Date:** June 2026

---

## What This Does

A machine learning pipeline that monitors SKU-level inventory across Bangalore dark stores and predicts urgent reorder events **before stockout occurs**. On a positive prediction, the system publishes an `AUTOMATED_PO_TRIGGERED` event to a Kafka topic for downstream purchase order generation.

This moves replenishment from **reactive** (stockout already happened) to **proactive** (reorder fired in advance based on velocity and stock signals).

---

## Folder Structure

```
replenishment-engine/
│
├── REprototype.ipynb                        # Main notebook (training + inference demo)
├── predictive_replenishment_model.pkl       # Serialized XGBoost model artifact
├── README.md                                # This file
```

---

## How to Run

### 1. Train the model & verify inference (Notebook)
Open `REprototype.ipynb` and run all cells in order:
- **Cell 1** — Generates synthetic data, trains XGBoost model, saves `.pkl` artifact
- **Cell 2** — Fires two mock telemetry payloads and prints inference output
- **Cell 3** — Starts the FastAPI service with Kafka integration

### 2. Start the API server
```bash
pip install fastapi uvicorn kafka-python xgboost scikit-learn joblib pandas
python -c "import uvicorn; uvicorn.run('REprototype:app', host='0.0.0.0', port=8000)"
```
Interactive API docs available at: `http://localhost:8000/docs`

---

## API Reference

### `POST /api/v1/inventory/check`

Accepts a SKU telemetry payload, runs inference, and publishes to Kafka if reorder is needed.

**Request:**
```json
{
  "sku_id": "ACS-45566",
  "On_Hand": 1,
  "Reserved": 0,
  "Daily_Velocity": 10.00,
  "Dark_Store_ID_DS_BLR_01": 1,
  "Dark_Store_ID_DS_BLR_02": 0,
  "Dark_Store_ID_DS_BLR_03": 0,
  "Temp_Zone_Ambient": 1,
  "Temp_Zone_Chilled": 0,
  "Temp_Zone_Frozen": 0
}
```

**Response — urgent reorder:**
```json
{
  "event_type": "AUTOMATED_PO_TRIGGERED",
  "confidence_score": 0.9928,
  "action": "GENERATE_PURCHASE_ORDER",
  "kafka_status": "published"
}
```

**Response — stock healthy:**
```json
{
  "status": "Inventory levels stable.",
  "kafka_status": "no_event"
}
```

---

## Kafka Integration

| Parameter | Value |
|---|---|
| Topic | `replenishment-events` |
| Broker | `localhost:9092` *(update to internal broker before deploy)* |
| Serialization | JSON (UTF-8) |

The HTTP endpoint is an **ingestion surface only**. The downstream PO system should consume exclusively from the Kafka topic, keeping the engine decoupled from dependent services.

---

## Model Details

| Parameter | Value |
|---|---|
| Algorithm | XGBoost Classifier |
| `n_estimators` | 100 |
| `max_depth` | 5 |
| `learning_rate` | 0.1 |
| `eval_metric` | logloss |
| Train / Test split | 80 / 20 |
| Artifact | `predictive_replenishment_model.pkl` |

**Features used at inference:** `On_Hand`, `Reserved`, `Daily_Velocity`, `Dark_Store_ID_*` (one-hot), `Temp_Zone_*` (one-hot)

**Intentionally excluded:** `Available` (= On_Hand − Reserved) and `Reorder_Level` — both are direct derivations of the target label and would cause data leakage.

---

## Known Limitations

| Limitation | Planned Fix |
|---|---|
| Synthetic training data | Replace with real transaction logs + rolling 7/14-day velocity averages |
| No lead time logic | Add per-SKU warehouse lead time buffer to fire reorders earlier |
| No evaluation metrics | Add `classification_report` + feature importance plot |
| Kafka broker hardcoded | Move to environment variable (`KAFKA_BROKER_URL`) |
| Single-store coverage | Extend to all Bangalore dark store locations |

---

## Dependencies

```
pandas
numpy
xgboost
scikit-learn
joblib
fastapi
uvicorn
kafka-python
```

---

## Contact

Jai Jain — ML Intern, Assesco Living
