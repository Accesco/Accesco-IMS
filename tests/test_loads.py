import pytest

from app.modules.loads.schemas import ERPOrderInput, ConsolidationRequest
from app.modules.loads.service import LoadConsolidationService


def _order(ref, lane, weight, volume, deadline):
    return ERPOrderInput(order_ref=ref, lane_id=lane, weight_kg=weight, volume_cbm=volume, deadline_hour=deadline)


def test_consolidate_packs_normal_orders():
    service = LoadConsolidationService()
    orders = [
        _order("A", "LANE-BLR-HYD", 500.0, 3.0, 10.0),
        _order("B", "LANE-BLR-HYD", 400.0, 2.5, 15.0),
    ]
    result = service.consolidate(orders)

    assert result.summary.n_trucks == 1
    assert result.summary.n_orders_packed == 2
    assert result.summary.n_oversized_orders == 0
    assert result.loads[0].n_orders == 2


def test_consolidate_flags_oversized_orders():
    service = LoadConsolidationService()
    orders = [
        _order("NORMAL", "LANE-BLR-HYD", 500.0, 3.0, 10.0),
        _order("OVER-WEIGHT", "LANE-BLR-HYD", 25000.0, 10.0, 5.0),
        _order("OVER-VOLUME", "LANE-BLR-HYD", 100.0, 80.0, 8.0),
    ]
    result = service.consolidate(orders)

    assert set(result.oversized_order_refs) == {"OVER-WEIGHT", "OVER-VOLUME"}
    assert result.summary.n_orders_packed == 1


def test_consolidate_orders_stops_by_deadline():
    service = LoadConsolidationService()
    orders = [
        _order("LATE", "LANE-BLR-CHN", 300.0, 2.0, 40.0),
        _order("EARLY", "LANE-BLR-CHN", 300.0, 2.0, 5.0),
        _order("MID", "LANE-BLR-CHN", 300.0, 2.0, 20.0),
    ]
    result = service.consolidate(orders)

    assert result.loads[0].order_refs_by_deadline == ["EARLY", "MID", "LATE"]


def test_consolidate_separates_by_lane():
    service = LoadConsolidationService()
    orders = [
        _order("A", "LANE-BLR-HYD", 500.0, 3.0, 10.0),
        _order("B", "LANE-BLR-CHN", 500.0, 3.0, 10.0),
    ]
    result = service.consolidate(orders)

    assert result.summary.n_trucks == 2
    assert {l.lane_id for l in result.loads} == {"LANE-BLR-HYD", "LANE-BLR-CHN"}


def test_schema_rejects_non_positive_weight():
    with pytest.raises(Exception):
        _order("BAD", "LANE-BLR-HYD", 0.0, 3.0, 10.0)


def test_schema_rejects_empty_order_list():
    with pytest.raises(Exception):
        ConsolidationRequest(orders=[])
