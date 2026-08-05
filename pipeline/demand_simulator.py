"""
demand_simulator.py
--------------------
Stage 1 (SPLIT) of the batching pipeline.

Generates a synthetic stream of Order objects for a single dark store.
Each order carries a minute-based arrival clock (arrival_min) so
batching_engine.py can run a discrete-time simulation over it.

Design choices (see chat history for the full list of assumptions):
  - Orders arrive as a Poisson process across a simulation window
    (sim_minutes) at a given arrival_rate_per_min. If no rate is
    given, one is derived from a daily-volume scenario
    (conservative/moderate/optimistic = 40/65/90 orders/day) spread
    across a 12h operating window.
  - 80% of orders cluster around 6 fixed "hotspots" (apartment
    complexes); 20% are uniform background noise across the zone.
  - Vertical (quadrant) is derived from geo_utils.classify_vertical:
    N/S x E/W relative to the store.
  - Pincode is a crude east/west placeholder (560103 / 560035) until
    real GIS polygons are available.
  - Delivery mode: 65% instant_10 (sla_min=10) / 35% scheduled_25
    (sla_min=25).
  - item_count: 1-4 items per order, uniform (placeholder — no real
    basket-size data yet).

Usage:
    python demand_simulator.py --sim-minutes 180 --rate 0.9 --seed 42
    python demand_simulator.py --sim-minutes 180 --scenario moderate --seed 42
"""

import argparse
import math
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from geo_utils import (
    DarkStore,
    VERTICALS,
    HALF_EXTENT_KM,
    km_per_degree,
    classify_vertical,
    clip_to_zone,
)

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------

# Daily order volume per scenario (from the report's table). Only used
# to derive a default arrival rate when --rate / arrival_rate_per_min
# isn't given directly.
SCENARIOS = {
    "conservative": 40,
    "moderate": 65,
    "optimistic": 90,
}
DEFAULT_OPERATING_HOURS = 12.0  # used only for scenario -> rate conversion

# Placeholder dark store location (Sarjapur/Bellandur belt, Bengaluru).
# SWAP THIS for your actual store's coordinates.
STORE_LAT = 12.9250
STORE_LON = 77.6850
STORE = DarkStore(name="Dark Store", lat=STORE_LAT, lon=STORE_LON)

KM_PER_DEG_LAT, KM_PER_DEG_LON = km_per_degree(STORE_LAT)

HOTSPOT_SHARE = 0.80
INSTANT_SHARE = 0.65
HOTSPOT_JITTER_KM = 0.25

SLA_MIN = {"instant_10": 10, "scheduled_25": 25}


@dataclass
class Hotspot:
    name: str
    d_lat_km: float  # offset from store, in km, north-positive
    d_lon_km: float  # offset from store, in km, east-positive


HOTSPOTS = [
    Hotspot("hotspot_A_NE", 1.10, 1.00),
    Hotspot("hotspot_B_NW", 1.05, -0.95),
    Hotspot("hotspot_C_SE", -1.00, 1.10),
    Hotspot("hotspot_D_SW", -1.15, -1.05),
    # E_N and S were originally at +/-1.30 km, only ~1.1 std devs from
    # the +/-1.581 km zone wall given HOTSPOT_JITTER_KM=0.25 -- close
    # enough that hard-clipping in clip_to_zone() created an artificial
    # pileup of orders sitting exactly on the boundary line (~2% of all
    # orders in a 97-order sample). Widened to +/-1.00 km so the jitter
    # comfortably stays clear of the wall (~2.3 std devs), matching the
    # other four hotspots.
    Hotspot("hotspot_E_N", 1.00, 0.10),
    Hotspot("hotspot_F_S", -1.00, -0.10),
]


@dataclass
class Order:
    order_id: str
    arrival_min: float       # minutes since simulation start
    lat: float
    lon: float
    vertical: str            # NE / NW / SE / SW
    pincode: str
    delivery_mode: str       # instant_10 / scheduled_25
    sla_min: int
    item_count: int
    source: str              # "hotspot" or "background" (for QA/debugging)


def assign_pincode(d_lon_km: float) -> str:
    """Placeholder pincode assignment: east of the store -> 560103,
    west -> 560035. Replace with real polygon lookups once GIS
    boundary files exist."""
    return "560103" if d_lon_km >= 0 else "560035"


def simulate_orders(
    sim_minutes: int = 180,
    arrival_rate_per_min: Optional[float] = None,
    scenario: str = "moderate",
    seed: Optional[int] = 42,
) -> List[Order]:
    """
    Generate a synthetic order stream over `sim_minutes` minutes.

    If arrival_rate_per_min is not given, it's derived from the
    scenario's daily order count spread across a 12h operating window
    (SCENARIOS[scenario] / DEFAULT_OPERATING_HOURS / 60).
    """
    if arrival_rate_per_min is None:
        if scenario not in SCENARIOS:
            raise ValueError(f"scenario must be one of {list(SCENARIOS)}, got {scenario!r}")
        arrival_rate_per_min = SCENARIOS[scenario] / DEFAULT_OPERATING_HOURS / 60.0

    if arrival_rate_per_min <= 0:
        raise ValueError("arrival_rate_per_min must be > 0")

    rng = np.random.default_rng(seed)

    orders: List[Order] = []
    t = 0.0
    idx = 0
    while True:
        gap = rng.exponential(scale=1.0 / arrival_rate_per_min)
        t += gap
        if t >= sim_minutes:
            break
        idx += 1

        is_hotspot = rng.random() < HOTSPOT_SHARE
        if is_hotspot:
            hs = HOTSPOTS[rng.integers(0, len(HOTSPOTS))]
            d_lat_km = rng.normal(hs.d_lat_km, HOTSPOT_JITTER_KM)
            d_lon_km = rng.normal(hs.d_lon_km, HOTSPOT_JITTER_KM)
            source = "hotspot"
        else:
            d_lat_km = rng.uniform(-HALF_EXTENT_KM, HALF_EXTENT_KM)
            d_lon_km = rng.uniform(-HALF_EXTENT_KM, HALF_EXTENT_KM)
            source = "background"
        d_lat_km, d_lon_km = clip_to_zone(d_lat_km, d_lon_km)

        lat = STORE_LAT + d_lat_km / KM_PER_DEG_LAT
        lon = STORE_LON + d_lon_km / KM_PER_DEG_LON

        mode = "instant_10" if rng.random() < INSTANT_SHARE else "scheduled_25"
        item_count = int(rng.integers(1, 5))  # 1-4 items

        orders.append(
            Order(
                order_id=f"ORD{idx:05d}",
                arrival_min=round(t, 4),
                lat=round(lat, 6),
                lon=round(lon, 6),
                vertical=classify_vertical(d_lat_km, d_lon_km),
                pincode=assign_pincode(d_lon_km),
                delivery_mode=mode,
                sla_min=SLA_MIN[mode],
                item_count=item_count,
                source=source,
            )
        )

    return orders


# ---------------------------------------------------------------------
# CLI (quick standalone sanity check)
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Stage 1: synthetic demand simulator")
    parser.add_argument("--sim-minutes", type=int, default=180, help="Simulation window in minutes (default: 180)")
    parser.add_argument("--rate", type=float, default=None, help="Orders per minute (overrides --scenario)")
    parser.add_argument("--scenario", choices=list(SCENARIOS), default="moderate")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    orders = simulate_orders(
        sim_minutes=args.sim_minutes,
        arrival_rate_per_min=args.rate,
        scenario=args.scenario,
        seed=args.seed,
    )

    print(f"Generated {len(orders)} orders over {args.sim_minutes} minutes")
    from collections import Counter
    print("Vertical distribution:", Counter(o.vertical for o in orders))
    print("Mode distribution:", Counter(o.delivery_mode for o in orders))
    print("Source distribution:", Counter(o.source for o in orders))


if __name__ == "__main__":
    main()
