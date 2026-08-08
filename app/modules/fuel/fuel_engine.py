"""
Fuel consumption estimation engine.

Deterministic formula (not ML -- no historical fuel-log data exists to
train against), combining base consumption, load weight, terrain
proxy, and optional congestion signal. See chat history for full
rationale. Embedded directly in this module rather than split into a
separate service -- same reasoning as app/modules/loads.
"""

from dataclasses import dataclass
from typing import Optional, Dict

# --- Lane reference data ----------------------------------------------------
# Mirrors fleet_lanes.py's synthetic network (kept as a small local copy
# so this module has no dependency on the eta-engine/ folder; swap for
# a shared lanes table once real facility data exists).

LANES: Dict[str, dict] = {
    "LANE-BLR-CHN": {"distance_km": 345.0, "free_flow_speed_max": 80.0},
    "LANE-BLR-HYD": {"distance_km": 570.0, "free_flow_speed_max": 85.0},
    "LANE-BLR-COK": {"distance_km": 460.0, "free_flow_speed_max": 75.0},
    "LANE-BLR-PUN": {"distance_km": 840.0, "free_flow_speed_max": 85.0},
    "LANE-BLR-MAA": {"distance_km": 350.0, "free_flow_speed_max": 70.0},  # ghats/curves -> lower ceiling
    "LANE-BLR-VJA": {"distance_km": 430.0, "free_flow_speed_max": 80.0},
}

MAX_WEIGHT_KG = 18000.0

BASE_CONSUMPTION_L_PER_100KM = 28.0
MAX_LOAD_PENALTY_L_PER_100KM = 9.0
MAX_TERRAIN_PENALTY_L_PER_100KM = 6.0
MAX_CONGESTION_PENALTY_L_PER_100KM = 5.0

_FASTEST_CEILING_KMPH = max(l["free_flow_speed_max"] for l in LANES.values())


@dataclass
class FuelEstimate:
    lane_id: str
    distance_km: float
    total_weight_kg: float
    consumption_l_per_100km: float
    liters_consumed: float
    base_l_per_100km: float
    load_penalty_l_per_100km: float
    terrain_penalty_l_per_100km: float
    congestion_penalty_l_per_100km: float
    cost_estimate: Optional[float] = None


def _terrain_penalty(free_flow_speed_max: float) -> float:
    ceiling_ratio = free_flow_speed_max / _FASTEST_CEILING_KMPH
    return MAX_TERRAIN_PENALTY_L_PER_100KM * (1.0 - ceiling_ratio)


def _congestion_penalty(free_flow_speed_max: float, avg_speed_kmh: Optional[float]) -> float:
    if avg_speed_kmh is None:
        return 0.0
    shortfall_ratio = max(0.0, (free_flow_speed_max - avg_speed_kmh) / free_flow_speed_max)
    return MAX_CONGESTION_PENALTY_L_PER_100KM * min(shortfall_ratio, 1.0)


def estimate_fuel(
    lane_id: str,
    total_weight_kg: float,
    avg_speed_kmh: Optional[float] = None,
    fuel_price_per_liter: Optional[float] = None,
) -> FuelEstimate:
    if lane_id not in LANES:
        raise ValueError(f"Unknown lane_id: {lane_id!r}")
    if total_weight_kg < 0:
        raise ValueError("total_weight_kg must be >= 0")
    if total_weight_kg > MAX_WEIGHT_KG:
        raise ValueError(f"total_weight_kg ({total_weight_kg}) exceeds truck capacity ({MAX_WEIGHT_KG})")

    lane = LANES[lane_id]
    ceiling = lane["free_flow_speed_max"]

    load_penalty = MAX_LOAD_PENALTY_L_PER_100KM * (total_weight_kg / MAX_WEIGHT_KG)
    terrain_penalty = _terrain_penalty(ceiling)
    congestion_penalty = _congestion_penalty(ceiling, avg_speed_kmh)

    consumption_l_per_100km = (
        BASE_CONSUMPTION_L_PER_100KM + load_penalty + terrain_penalty + congestion_penalty
    )
    liters_consumed = consumption_l_per_100km * (lane["distance_km"] / 100.0)

    cost_estimate = (
        round(liters_consumed * fuel_price_per_liter, 2) if fuel_price_per_liter is not None else None
    )

    return FuelEstimate(
        lane_id=lane_id,
        distance_km=lane["distance_km"],
        total_weight_kg=total_weight_kg,
        consumption_l_per_100km=round(consumption_l_per_100km, 2),
        liters_consumed=round(liters_consumed, 2),
        base_l_per_100km=round(BASE_CONSUMPTION_L_PER_100KM, 2),
        load_penalty_l_per_100km=round(load_penalty, 2),
        terrain_penalty_l_per_100km=round(terrain_penalty, 2),
        congestion_penalty_l_per_100km=round(congestion_penalty, 2),
        cost_estimate=cost_estimate,
    )
