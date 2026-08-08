"""
Unit tests for the Maintenance Drift Engine API.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch


@pytest.fixture(scope="module")
def client():
    """
    MODEL_PATH is resolved as an absolute path relative to THIS FILE's
    location, not the process's current working directory -- same fix
    applied to eta-api/tests/test_api.py, same reason (CWD-relative
    paths break depending on how/where CI invokes pytest).
    """
    import os
    this_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.normpath(os.path.join(this_dir, "..", "maintenance_drift_model.joblib"))
    os.environ["MODEL_PATH"] = model_path
    from main import app
    with TestClient(app) as c:
        yield c


VALID_PAYLOAD = {
    "lane_id": "LANE-BLR-MAA",
    "terrain_factor": 1.0,
    "vehicle_age_years": 6.0,
    "km_since_last_service": 4000.0,
    "days_since_last_service": 90,
    "avg_daily_km_this_interval": 400.0,
    "avg_load_utilization_pct": 80.0,
    "harsh_events_per_1000km": 12.0,
}


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert len(body["model_features"]) == 8


def test_valid_request_returns_200(client):
    response = client.post("/predict-maintenance", json=VALID_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert "naive_km_remaining" in body
    assert "predicted_drift_km" in body
    assert "corrected_km_remaining" in body


def test_corrected_equals_naive_plus_drift(client):
    response = client.post("/predict-maintenance", json=VALID_PAYLOAD)
    body = response.json()
    assert body["corrected_km_remaining"] == pytest.approx(
        body["naive_km_remaining"] + body["predicted_drift_km"], abs=0.1
    )


def test_naive_km_remaining_matches_fixed_interval_formula(client):
    response = client.post("/predict-maintenance", json=VALID_PAYLOAD)
    body = response.json()
    assert body["naive_km_remaining"] == pytest.approx(
        10000.0 - VALID_PAYLOAD["km_since_last_service"], abs=0.1
    )


def test_heavy_use_gets_bigger_correction_than_gentle_use(client):
    heavy = client.post("/predict-maintenance", json=VALID_PAYLOAD).json()
    gentle_payload = {
        **VALID_PAYLOAD,
        "lane_id": "LANE-BLR-PUN",
        "terrain_factor": 0.0,
        "vehicle_age_years": 1.0,
        "avg_load_utilization_pct": 40.0,
        "harsh_events_per_1000km": 1.0,
    }
    gentle = client.post("/predict-maintenance", json=gentle_payload).json()
    assert abs(heavy["predicted_drift_km"]) > abs(gentle["predicted_drift_km"])


def test_missing_required_field_returns_422(client):
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "lane_id"}
    response = client.post("/predict-maintenance", json=payload)
    assert response.status_code == 422


def test_negative_km_since_service_returns_422(client):
    payload = {**VALID_PAYLOAD, "km_since_last_service": -100.0}
    response = client.post("/predict-maintenance", json=payload)
    assert response.status_code == 422


def test_out_of_range_terrain_factor_returns_422(client):
    payload = {**VALID_PAYLOAD, "terrain_factor": 1.5}
    response = client.post("/predict-maintenance", json=payload)
    assert response.status_code == 422


def test_out_of_range_load_utilization_returns_422(client):
    payload = {**VALID_PAYLOAD, "avg_load_utilization_pct": 150.0}
    response = client.post("/predict-maintenance", json=payload)
    assert response.status_code == 422


def test_empty_body_returns_422(client):
    response = client.post("/predict-maintenance", json={})
    assert response.status_code == 422


def test_model_loaded_once_on_startup(client):
    with patch("inference.joblib.load") as mock_load:
        client.post("/predict-maintenance", json=VALID_PAYLOAD)
        client.post("/predict-maintenance", json={**VALID_PAYLOAD, "vehicle_age_years": 2.0})
        mock_load.assert_not_called()
