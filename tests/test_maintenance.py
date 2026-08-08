import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.modules.maintenance.service import MaintenanceService
from app.modules.maintenance.ml_client import build_ml_payload, call_ml_engine
from app.modules.maintenance.schemas import MaintenancePredictRequest
from app.core.exceptions import MLServiceUnavailableException


def _make_request(**overrides):
    defaults = dict(
        vehicle_id="VEH-0001",
        lane_id="LANE-BLR-MAA",
        terrain_factor=1.0,
        vehicle_age_years=6.0,
        km_since_last_service=4000.0,
        days_since_last_service=90,
        avg_daily_km_this_interval=400.0,
        avg_load_utilization_pct=80.0,
        harsh_events_per_1000km=12.0,
    )
    defaults.update(overrides)
    return MaintenancePredictRequest(**defaults)


MOCK_ML_RESPONSE = {
    "naive_km_remaining": 6000.0,
    "predicted_drift_km": -4682.7,
    "corrected_km_remaining": 1317.3,
}


class TestBuildMLPayload:
    def test_basic_payload(self):
        payload = build_ml_payload(
            lane_id="LANE-BLR-MAA", terrain_factor=1.0, vehicle_age_years=6.0,
            km_since_last_service=4000.0, days_since_last_service=90,
            avg_daily_km_this_interval=400.0, avg_load_utilization_pct=80.0,
            harsh_events_per_1000km=12.0,
        )
        assert payload["lane_id"] == "LANE-BLR-MAA"
        assert payload["terrain_factor"] == 1.0


class TestCallMLEngine:
    @pytest.mark.asyncio
    async def test_successful_call(self):
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.return_value = httpx.Response(
                200, json=MOCK_ML_RESPONSE,
                request=httpx.Request("POST", "http://test/predict-maintenance"),
            )
            result = await call_ml_engine({"lane_id": "LANE-BLR-MAA"})
            assert result == MOCK_ML_RESPONSE

    @pytest.mark.asyncio
    async def test_timeout_raises_service_unavailable(self):
        with patch("httpx.AsyncClient.post", side_effect=httpx.TimeoutException("timed out")):
            with pytest.raises(MLServiceUnavailableException):
                await call_ml_engine({"lane_id": "LANE-BLR-MAA"})

    @pytest.mark.asyncio
    async def test_connect_error_raises_service_unavailable(self):
        with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("refused")):
            with pytest.raises(MLServiceUnavailableException):
                await call_ml_engine({"lane_id": "LANE-BLR-MAA"})


@pytest.mark.asyncio
async def test_predict_returns_response():
    service = MaintenanceService()
    with patch("app.modules.maintenance.service.call_ml_engine", new=AsyncMock(return_value=MOCK_ML_RESPONSE)):
        result = await service.predict(_make_request())

    assert result.vehicle_id == "VEH-0001"
    assert result.corrected_km_remaining == 1317.3


@pytest.mark.asyncio
async def test_predict_propagates_ml_service_unavailable():
    service = MaintenanceService()
    with patch(
        "app.modules.maintenance.service.call_ml_engine",
        new=AsyncMock(side_effect=MLServiceUnavailableException("engine down")),
    ):
        with pytest.raises(MLServiceUnavailableException):
            await service.predict(_make_request())
