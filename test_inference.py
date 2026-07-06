"""
Unit tests for ReplenishmentInferenceService in isolation.
These tests do NOT start the FastAPI server — they test the inference
class directly, making them faster and independent of HTTP concerns.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from schemas import ReplenishmentRequest, ReplenishmentResponse
from inference import ReplenishmentInferenceService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

EXPECTED_FEATURES = [
    "On_Hand", "Reserved", "Daily_Velocity",
    "Dark_Store_ID_DS-BLR-01", "Dark_Store_ID_DS-BLR-02", "Dark_Store_ID_DS-BLR-03",
    "Temp_Zone_Ambient", "Temp_Zone_Chilled", "Temp_Zone_Frozen",
]

@pytest.fixture
def mock_service():
    """Returns a ReplenishmentInferenceService with a mocked model."""
    with patch("inference.joblib.load") as mock_load:
        mock_model = MagicMock()
        mock_model.get_booster.return_value.feature_names = EXPECTED_FEATURES
        mock_load.return_value = mock_model
        service = ReplenishmentInferenceService("dummy_model.pkl")
        service._mock_model = mock_model
        yield service


def make_request(**overrides):
    defaults = {
        "sku_id": "ACS-45566",
        "store_id": "DS-BLR-01",
        "on_hand": 1,
        "reserved": 0,
        "daily_velocity": 10.0,
        "temp_zone": "Ambient",
    }
    return ReplenishmentRequest(**{**defaults, **overrides})


# ---------------------------------------------------------------------------
# Feature construction
# ---------------------------------------------------------------------------

def test_feature_row_has_correct_column_count(mock_service):
    request = make_request()
    df = mock_service._build_feature_row(request)
    assert df.shape == (1, 9)


def test_feature_row_columns_match_training_schema(mock_service):
    request = make_request()
    df = mock_service._build_feature_row(request)
    assert list(df.columns) == EXPECTED_FEATURES


def test_store_id_one_hot_encoding_ds_blr_01(mock_service):
    request = make_request(store_id="DS-BLR-01")
    df = mock_service._build_feature_row(request)
    assert df["Dark_Store_ID_DS-BLR-01"].iloc[0] == 1
    assert df["Dark_Store_ID_DS-BLR-02"].iloc[0] == 0
    assert df["Dark_Store_ID_DS-BLR-03"].iloc[0] == 0


def test_store_id_one_hot_encoding_ds_blr_02(mock_service):
    request = make_request(store_id="DS-BLR-02")
    df = mock_service._build_feature_row(request)
    assert df["Dark_Store_ID_DS-BLR-02"].iloc[0] == 1
    assert df["Dark_Store_ID_DS-BLR-01"].iloc[0] == 0


def test_temp_zone_one_hot_encoding_ambient(mock_service):
    request = make_request(temp_zone="Ambient")
    df = mock_service._build_feature_row(request)
    assert df["Temp_Zone_Ambient"].iloc[0] == 1
    assert df["Temp_Zone_Chilled"].iloc[0] == 0
    assert df["Temp_Zone_Frozen"].iloc[0] == 0


def test_temp_zone_one_hot_encoding_frozen(mock_service):
    request = make_request(temp_zone="Frozen")
    df = mock_service._build_feature_row(request)
    assert df["Temp_Zone_Frozen"].iloc[0] == 1
    assert df["Temp_Zone_Ambient"].iloc[0] == 0


def test_numeric_features_passed_correctly(mock_service):
    request = make_request(on_hand=42, reserved=5, daily_velocity=7.5)
    df = mock_service._build_feature_row(request)
    assert df["On_Hand"].iloc[0] == 42
    assert df["Reserved"].iloc[0] == 5
    assert df["Daily_Velocity"].iloc[0] == 7.5


# ---------------------------------------------------------------------------
# Prediction output
# ---------------------------------------------------------------------------

def test_predict_returns_urgent_reorder_true(mock_service):
    mock_service._mock_model.predict.return_value = np.array([1])
    mock_service._mock_model.predict_proba.return_value = np.array([[0.05, 0.95]])
    result = mock_service.predict(make_request())
    assert result.urgent_reorder is True
    assert result.action == "GENERATE_PURCHASE_ORDER"


def test_predict_returns_urgent_reorder_false(mock_service):
    mock_service._mock_model.predict.return_value = np.array([0])
    mock_service._mock_model.predict_proba.return_value = np.array([[0.92, 0.08]])
    result = mock_service.predict(make_request())
    assert result.urgent_reorder is False
    assert result.action == "NO_ACTION_REQUIRED"


def test_predict_echoes_sku_and_store(mock_service):
    mock_service._mock_model.predict.return_value = np.array([1])
    mock_service._mock_model.predict_proba.return_value = np.array([[0.01, 0.99]])
    result = mock_service.predict(make_request(sku_id="ACS-99999", store_id="DS-BLR-03"))
    assert result.sku_id == "ACS-99999"
    assert result.store_id == "DS-BLR-03"


def test_confidence_score_rounded_to_4dp(mock_service):
    mock_service._mock_model.predict.return_value = np.array([1])
    mock_service._mock_model.predict_proba.return_value = np.array([[0.0, 0.992812345]])
    result = mock_service.predict(make_request())
    assert result.confidence_score == round(result.confidence_score, 4)


def test_predict_returns_replenishment_response_type(mock_service):
    mock_service._mock_model.predict.return_value = np.array([0])
    mock_service._mock_model.predict_proba.return_value = np.array([[0.8, 0.2]])
    result = mock_service.predict(make_request())
    assert isinstance(result, ReplenishmentResponse)
