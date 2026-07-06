"""
Unit tests for the Predictive Replenishment Engine API.

Covers:
  - Valid low-stock request → urgent_reorder: true
  - Valid healthy-stock request → urgent_reorder: false
  - Response schema contract (all required fields present)
  - Validation errors for missing / invalid fields
  - Health check endpoint
  - Model loaded once (not per request)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from schemas import ReplenishmentRequest, ReplenishmentResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """
    Starts the FastAPI test client with the real model loaded from the
    pkl file in the project root.
    """
    import os
    os.environ["MODEL_PATH"] = "predictive_replenishment_model.pkl"
    from main import app
    with TestClient(app) as c:
        yield c


LOW_STOCK_PAYLOAD = {
    "sku_id": "ACS-45566",
    "store_id": "DS-BLR-01",
    "on_hand": 1,
    "reserved": 0,
    "daily_velocity": 10.0,
    "temp_zone": "Ambient",
}

HEALTHY_STOCK_PAYLOAD = {
    "sku_id": "ACS-99682",
    "store_id": "DS-BLR-01",
    "on_hand": 117,
    "reserved": 11,
    "daily_velocity": 14.32,
    "temp_zone": "Ambient",
}


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert isinstance(body["model_features"], list)
    assert len(body["model_features"]) == 9


# ---------------------------------------------------------------------------
# Prediction — correct outputs
# ---------------------------------------------------------------------------

def test_low_stock_returns_urgent_reorder(client):
    """Low on_hand + high velocity should trigger urgent reorder."""
    response = client.post("/predict-replenishment", json=LOW_STOCK_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body["urgent_reorder"] is True
    assert body["action"] == "GENERATE_PURCHASE_ORDER"


def test_healthy_stock_returns_no_action(client):
    """High on_hand + moderate velocity should return no action."""
    response = client.post("/predict-replenishment", json=HEALTHY_STOCK_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert body["urgent_reorder"] is False
    assert body["action"] == "NO_ACTION_REQUIRED"


# ---------------------------------------------------------------------------
# Response schema contract
# ---------------------------------------------------------------------------

def test_response_contains_all_required_fields(client):
    response = client.post("/predict-replenishment", json=LOW_STOCK_PAYLOAD)
    body = response.json()
    for field in ["sku_id", "store_id", "urgent_reorder", "confidence_score", "action"]:
        assert field in body, f"Missing field: {field}"


def test_response_echoes_sku_and_store_id(client):
    response = client.post("/predict-replenishment", json=LOW_STOCK_PAYLOAD)
    body = response.json()
    assert body["sku_id"] == LOW_STOCK_PAYLOAD["sku_id"]
    assert body["store_id"] == LOW_STOCK_PAYLOAD["store_id"]


def test_confidence_score_is_between_0_and_1(client):
    response = client.post("/predict-replenishment", json=LOW_STOCK_PAYLOAD)
    score = response.json()["confidence_score"]
    assert 0.0 <= score <= 1.0


def test_confidence_score_rounded_to_4_decimal_places(client):
    response = client.post("/predict-replenishment", json=LOW_STOCK_PAYLOAD)
    score = response.json()["confidence_score"]
    assert score == round(score, 4)


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

def test_missing_required_field_returns_422(client):
    """Omitting sku_id should return a validation error."""
    payload = {k: v for k, v in LOW_STOCK_PAYLOAD.items() if k != "sku_id"}
    response = client.post("/predict-replenishment", json=payload)
    assert response.status_code == 422


def test_invalid_store_id_returns_422(client):
    """store_id must be one of the three known dark stores."""
    payload = {**LOW_STOCK_PAYLOAD, "store_id": "DS-MUM-99"}
    response = client.post("/predict-replenishment", json=payload)
    assert response.status_code == 422


def test_invalid_temp_zone_returns_422(client):
    payload = {**LOW_STOCK_PAYLOAD, "temp_zone": "Tropical"}
    response = client.post("/predict-replenishment", json=payload)
    assert response.status_code == 422


def test_negative_on_hand_returns_422(client):
    payload = {**LOW_STOCK_PAYLOAD, "on_hand": -5}
    response = client.post("/predict-replenishment", json=payload)
    assert response.status_code == 422


def test_zero_daily_velocity_returns_422(client):
    """daily_velocity must be > 0 to avoid division-by-zero in downstream logic."""
    payload = {**LOW_STOCK_PAYLOAD, "daily_velocity": 0.0}
    response = client.post("/predict-replenishment", json=payload)
    assert response.status_code == 422


def test_empty_body_returns_422(client):
    response = client.post("/predict-replenishment", json={})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Model loaded once — not per request
# ---------------------------------------------------------------------------

def test_model_loaded_once_on_startup(client):
    """
    Calls the endpoint twice and verifies joblib.load is NOT called during
    inference (it should have been called only during the lifespan startup).
    """
    with patch("inference.joblib.load") as mock_load:
        client.post("/predict-replenishment", json=LOW_STOCK_PAYLOAD)
        client.post("/predict-replenishment", json=HEALTHY_STOCK_PAYLOAD)
        mock_load.assert_not_called()


# ---------------------------------------------------------------------------
# All valid store_ids and temp_zones work
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("store_id", ["DS-BLR-01", "DS-BLR-02", "DS-BLR-03"])
def test_all_store_ids_accepted(client, store_id):
    payload = {**LOW_STOCK_PAYLOAD, "store_id": store_id}
    response = client.post("/predict-replenishment", json=payload)
    assert response.status_code == 200


@pytest.mark.parametrize("temp_zone", ["Ambient", "Chilled", "Frozen"])
def test_all_temp_zones_accepted(client, temp_zone):
    payload = {**LOW_STOCK_PAYLOAD, "temp_zone": temp_zone}
    response = client.post("/predict-replenishment", json=payload)
    assert response.status_code == 200
