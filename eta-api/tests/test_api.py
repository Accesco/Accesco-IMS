"""
Unit tests for the ETA Drift Engine API.

Covers:
  - Health check endpoint
  - Valid prediction request -> 200 with all three fields
  - Stopped-truck edge case (current_speed_kmh=0) handled, not a crash
  - Response schema contract
  - Validation errors for missing / out-of-range fields
  - Model loaded once (not per request)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """
    Starts the FastAPI test client with the real model loaded from the
    joblib file in the project root.
    """
    import os
    os.environ["MODEL_PATH"] = "eta_drift_model.joblib"
    from main import app
    with TestClient(app) as c:
        yield c


VALID_PAYLOAD = {
    "lane_id": "LANE-BLR-HYD",
    "carrier_id": "CARR-004",
    "carrier_on_time_score": 0.82,
    "hour_of_day": 8.5,
    "is_rush_hour": True,
    "distance_remaining_km": 410.0,
    "progress_fraction": 0.18,
    "current_speed_kmh": 32.0,
    "avg_speed_so_far_kmh": 48.0,
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
# Prediction -- correct outputs
# ---------------------------------------------------------------------------

def test_valid_request_returns_200(client):
    response = client.post("/predict-eta", json=VALID_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert "naive_eta_remaining_min" in body
    assert "predicted_drift_min" in body
    assert "corrected_eta_remaining_min" in body


def test_corrected_eta_equals_naive_plus_drift(client):
    response = client.post("/predict-eta", json=VALID_PAYLOAD)
    body = response.json()
    assert body["corrected_eta_remaining_min"] == pytest.approx(
        body["naive_eta_remaining_min"] + body["predicted_drift_min"], abs=0.01
    )


def test_stopped_truck_does_not_crash(client):
    """current_speed_kmh=0 is a normal real-world reading (red light,
    loading dock) -- must return 200, not 500/crash."""
    payload = {**VALID_PAYLOAD, "current_speed_kmh": 0.0}
    response = client.post("/predict-eta", json=payload)
    assert response.status_code == 200
    assert response.json()["naive_eta_remaining_min"] > 0


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

def test_missing_required_field_returns_422(client):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "lane_id"}
    response = client.post("/predict-eta", json=payload)
    assert response.status_code == 422


def test_negative_speed_returns_422(client):
    payload = {**VALID_PAYLOAD, "current_speed_kmh": -5.0}
    response = client.post("/predict-eta", json=payload)
    assert response.status_code == 422


def test_negative_distance_returns_422(client):
    payload = {**VALID_PAYLOAD, "distance_remaining_km": -10.0}
    response = client.post("/predict-eta", json=payload)
    assert response.status_code == 422


def test_out_of_range_hour_returns_422(client):
    payload = {**VALID_PAYLOAD, "hour_of_day": 25.0}
    response = client.post("/predict-eta", json=payload)
    assert response.status_code == 422


def test_out_of_range_on_time_score_returns_422(client):
    payload = {**VALID_PAYLOAD, "carrier_on_time_score": 1.5}
    response = client.post("/predict-eta", json=payload)
    assert response.status_code == 422


def test_out_of_range_progress_fraction_returns_422(client):
    payload = {**VALID_PAYLOAD, "progress_fraction": 1.5}
    response = client.post("/predict-eta", json=payload)
    assert response.status_code == 422


def test_empty_body_returns_422(client):
    response = client.post("/predict-eta", json={})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Model loaded once -- not per request
# ---------------------------------------------------------------------------

def test_model_loaded_once_on_startup(client):
    """
    Calls the endpoint twice and verifies joblib.load is NOT called
    during inference (it should only be called during lifespan startup).
    """
    with patch("inference.joblib.load") as mock_load:
        client.post("/predict-eta", json=VALID_PAYLOAD)
        client.post("/predict-eta", json={**VALID_PAYLOAD, "current_speed_kmh": 60.0})
        mock_load.assert_not_called()
