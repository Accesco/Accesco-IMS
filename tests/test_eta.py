"""
Tests for the ETA module.

Covers:
- ML payload passthrough (build_ml_payload)
- ML client error handling (mocked httpx calls)
- Prediction persistence + retrieval (mocked ML engine, real DB)
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.eta import ETAPrediction
from app.modules.eta.service import ETAService
from app.modules.eta.repository import ETARepository
from app.modules.eta.ml_client import build_ml_payload, call_ml_engine
from app.modules.eta.schemas import ETAPredictRequest
from app.core.exceptions import ResourceNotFoundException, MLServiceUnavailableException


def _make_request(**overrides):
    defaults = dict(
        shipment_id="SHIP-00001",
        lane_id="LANE-BLR-HYD",
        carrier_id="CARR-004",
        carrier_on_time_score=0.82,
        hour_of_day=8.5,
        is_rush_hour=True,
        distance_remaining_km=410.0,
        progress_fraction=0.18,
        current_speed_kmh=32.0,
        avg_speed_so_far_kmh=48.0,
    )
    defaults.update(overrides)
    return ETAPredictRequest(**defaults)


MOCK_ML_RESPONSE = {
    "naive_eta_remaining_min": 768.75,
    "predicted_drift_min": -388.4,
    "corrected_eta_remaining_min": 380.35,
}


# ─── ML Client Tests ───────────────────────────────────────────────

class TestBuildMLPayload:
    def test_basic_payload(self):
        payload = build_ml_payload(
            lane_id="LANE-BLR-HYD",
            carrier_id="CARR-004",
            carrier_on_time_score=0.82,
            hour_of_day=8.5,
            is_rush_hour=True,
            distance_remaining_km=410.0,
            progress_fraction=0.18,
            current_speed_kmh=32.0,
            avg_speed_so_far_kmh=48.0,
        )
        assert payload["lane_id"] == "LANE-BLR-HYD"
        assert payload["carrier_id"] == "CARR-004"
        assert payload["is_rush_hour"] is True
        assert payload["distance_remaining_km"] == 410.0


class TestCallMLEngine:
    @pytest.mark.asyncio
    async def test_successful_call(self):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = httpx.Response(
                200, json=MOCK_ML_RESPONSE,
                request=httpx.Request("POST", "http://test/predict-eta"),
            )
            result = await call_ml_engine({"lane_id": "LANE-BLR-HYD"})
            assert result == MOCK_ML_RESPONSE

    @pytest.mark.asyncio
    async def test_timeout_raises_service_unavailable(self):
        with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("timed out")):
            with pytest.raises(MLServiceUnavailableException):
                await call_ml_engine({"lane_id": "LANE-BLR-HYD"})

    @pytest.mark.asyncio
    async def test_connect_error_raises_service_unavailable(self):
        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(MLServiceUnavailableException):
                await call_ml_engine({"lane_id": "LANE-BLR-HYD"})


# ─── Service / Persistence Tests ───────────────────────────────────

@pytest.mark.asyncio
async def test_predict_persists_and_returns_prediction(db_session: AsyncSession):
    service = ETAService(db_session)

    with patch("app.modules.eta.service.call_ml_engine", new=AsyncMock(return_value=MOCK_ML_RESPONSE)):
        prediction = await service.predict(_make_request())

    assert isinstance(prediction, ETAPrediction)
    assert prediction.id is not None
    assert prediction.shipment_id == "SHIP-00001"
    assert prediction.corrected_eta_remaining_min == 380.35
    assert prediction.ml_response_payload == MOCK_ML_RESPONSE


@pytest.mark.asyncio
async def test_get_prediction_by_id_not_found_raises(db_session: AsyncSession):
    service = ETAService(db_session)
    with pytest.raises(ResourceNotFoundException):
        await service.get_prediction_by_id(99999)


@pytest.mark.asyncio
async def test_get_predictions_filters_by_lane(db_session: AsyncSession):
    service = ETAService(db_session)

    with patch("app.modules.eta.service.call_ml_engine", new=AsyncMock(return_value=MOCK_ML_RESPONSE)):
        await service.predict(_make_request(lane_id="LANE-BLR-HYD"))
        await service.predict(_make_request(lane_id="LANE-BLR-CHN", shipment_id="SHIP-00002"))

    hyd_only = await service.get_predictions(lane_id="LANE-BLR-HYD")
    assert len(hyd_only) == 1
    assert hyd_only[0].lane_id == "LANE-BLR-HYD"

    all_predictions = await service.get_predictions()
    assert len(all_predictions) == 2


@pytest.mark.asyncio
async def test_predict_propagates_ml_service_unavailable(db_session: AsyncSession):
    """If the ETA Drift Engine is down, nothing should be persisted --
    the exception should propagate before repo.create_prediction runs."""
    service = ETAService(db_session)

    with patch(
        "app.modules.eta.service.call_ml_engine",
        new=AsyncMock(side_effect=MLServiceUnavailableException("engine down")),
    ):
        with pytest.raises(MLServiceUnavailableException):
            await service.predict(_make_request())

    all_predictions = await service.get_predictions()
    assert len(all_predictions) == 0
