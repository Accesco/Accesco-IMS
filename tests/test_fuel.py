import pytest
from fastapi import HTTPException

from app.modules.fuel.schemas import FuelEstimateRequest
from app.modules.fuel.service import FuelEstimationService


def test_estimate_full_load_flat_lane():
    service = FuelEstimationService()
    result = service.estimate(FuelEstimateRequest(lane_id="LANE-BLR-PUN", total_weight_kg=18000.0))
    assert result.load_penalty_l_per_100km == pytest.approx(9.0, abs=0.01)
    assert result.terrain_penalty_l_per_100km == pytest.approx(0.0, abs=0.01)


def test_estimate_hilly_lane_has_terrain_penalty():
    service = FuelEstimationService()
    result = service.estimate(FuelEstimateRequest(lane_id="LANE-BLR-MAA", total_weight_kg=0.0))
    assert result.terrain_penalty_l_per_100km > 0
    assert result.load_penalty_l_per_100km == 0.0


def test_estimate_congestion_only_applied_when_speed_given():
    service = FuelEstimationService()
    without_speed = service.estimate(FuelEstimateRequest(lane_id="LANE-BLR-HYD", total_weight_kg=10000.0))
    assert without_speed.congestion_penalty_l_per_100km == 0.0

    with_speed = service.estimate(FuelEstimateRequest(
        lane_id="LANE-BLR-HYD", total_weight_kg=10000.0, avg_speed_kmh=30.0
    ))
    assert with_speed.congestion_penalty_l_per_100km > 0


def test_estimate_cost_only_when_price_given():
    service = FuelEstimationService()
    no_price = service.estimate(FuelEstimateRequest(lane_id="LANE-BLR-HYD", total_weight_kg=10000.0))
    assert no_price.cost_estimate is None

    with_price = service.estimate(FuelEstimateRequest(
        lane_id="LANE-BLR-HYD", total_weight_kg=10000.0, fuel_price_per_liter=92.5
    ))
    assert with_price.cost_estimate == pytest.approx(with_price.liters_consumed * 92.5, abs=0.01)


def test_estimate_unknown_lane_raises_422():
    service = FuelEstimationService()
    with pytest.raises(HTTPException) as exc_info:
        service.estimate(FuelEstimateRequest(lane_id="LANE-DOES-NOT-EXIST", total_weight_kg=1000.0))
    assert exc_info.value.status_code == 422


def test_estimate_over_capacity_raises_422():
    service = FuelEstimationService()
    with pytest.raises(HTTPException) as exc_info:
        service.estimate(FuelEstimateRequest(lane_id="LANE-BLR-HYD", total_weight_kg=20000.0))
    assert exc_info.value.status_code == 422


def test_schema_rejects_negative_weight():
    with pytest.raises(Exception):
        FuelEstimateRequest(lane_id="LANE-BLR-HYD", total_weight_kg=-100.0)
