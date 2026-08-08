"""
vehicle_usage_simulator.py
----------------------------
Generates synthetic vehicle usage histories for the TMS maintenance
prediction feature.

No real vehicle telemetry/service-log data exists yet -- this
simulates full vehicle-life trajectories (so the true maintenance-due
point is known), then samples snapshots along each service interval
for training, exactly like fleet_telemetry_simulator.py did for the
ETA drift model.

Physical model: every fleet uses a nominal service interval
(BASE_INTERVAL_KM, "every 10,000 km" style), but actual wear
accumulates faster than 1:1 with physical distance depending on usage
intensity:
  - Load factor: heavier average loads stress the drivetrain/brakes/
    tires more per km.
  - Harsh driving events: hard braking/acceleration accelerates wear
    independent of load or distance.
  - Terrain: hilly/curvy routes wear brakes and drivetrain faster than
    flat highway, for the same distance.
  - Vehicle age: older vehicles accumulate wear faster per km than a
    newer one doing identical driving.

A naive "every 10,000 km" rule ignores all of this and is a
systematically biased estimator -- exactly the gap the ML model is
meant to learn and correct, framed the same way as the ETA drift
model (naive baseline + predicted correction).
"""

import argparse
import csv
from dataclasses import dataclass
from typing import List

import numpy as np

BASE_INTERVAL_KM = 10000.0

# Terrain proxy per primary lane (0 = flat/fast, 1 = hilliest) --
# mirrors fuel_engine.py's terrain treatment, kept as its own small
# reference here so this service has no cross-folder dependency on
# eta-engine/fleet_lanes.py (see chat history re: the CI import
# collision from shared filenames across sibling service folders --
# keeping services self-contained avoids that whole class of problem).
LANE_TERRAIN_FACTOR = {
    "LANE-BLR-CHN": 0.0,
    "LANE-BLR-HYD": 0.0,
    "LANE-BLR-COK": 0.2,
    "LANE-BLR-PUN": 0.0,
    "LANE-BLR-MAA": 1.0,  # ghats/curves
    "LANE-BLR-VJA": 0.0,
}

DAILY_KM_RANGE = (150.0, 550.0)  # typical line-haul truck daily distance
SIM_DAYS = 730  # ~2 years of usage history per vehicle


@dataclass
class Vehicle:
    vehicle_id: str
    primary_lane_id: str
    vehicle_age_years_at_start: float
    driving_harshness: float  # 0-1, persistent per-vehicle trait


def _make_vehicle(idx: int, rng: np.random.Generator) -> Vehicle:
    lane_id = rng.choice(list(LANE_TERRAIN_FACTOR.keys()))
    return Vehicle(
        vehicle_id=f"VEH-{idx:04d}",
        primary_lane_id=lane_id,
        vehicle_age_years_at_start=float(rng.uniform(0.5, 8.0)),
        driving_harshness=float(rng.beta(2, 5)),  # skewed toward gentler driving, long tail of harsh drivers
    )


def _wear_rate(load_utilization_pct: float, harshness: float, terrain_factor: float, age_years: float) -> float:
    """Multiplier on physical km to get "wear km" -- 1.0 means wear
    accumulates 1:1 with distance (the naive assumption); higher means
    faster-than-distance wear accumulation."""
    load_effect = 0.4 * (load_utilization_pct / 100.0)
    harshness_effect = 0.5 * harshness
    terrain_effect = 0.3 * terrain_factor
    age_effect = 0.02 * age_years
    return 1.0 + load_effect + harshness_effect + terrain_effect + age_effect


def simulate_vehicle(vehicle: Vehicle, rng: np.random.Generator) -> List[dict]:
    """
    Simulates one vehicle's full usage history (SIM_DAYS), tracking
    both physical km and wear-adjusted km. Each time wear-adjusted km
    crosses BASE_INTERVAL_KM, a service interval closes and a new one
    begins. Returns one training snapshot per day within each
    interval (so the "how much do we know so far this interval"
    features grow realistically day by day).
    """
    records = []

    km_since_service = 0.0
    wear_km_since_service = 0.0
    days_since_service = 0
    interval_daily_kms: List[float] = []
    interval_loads: List[float] = []
    interval_harsh_counts: List[int] = []
    interval_start_idx = 0  # index into `records` where the current interval began

    terrain_factor = LANE_TERRAIN_FACTOR[vehicle.primary_lane_id]
    age_years = vehicle.vehicle_age_years_at_start

    day = 0
    while day < SIM_DAYS:
        daily_km = float(rng.uniform(*DAILY_KM_RANGE))
        load_utilization_pct = float(np.clip(rng.normal(55.0, 20.0), 5.0, 100.0))
        # Harsh events roughly scale with the vehicle's persistent harshness trait, with day-to-day noise.
        expected_harsh_events = vehicle.driving_harshness * (daily_km / 100.0) * 2.0
        harsh_events_today = int(rng.poisson(max(expected_harsh_events, 0.01)))

        wear_rate = _wear_rate(load_utilization_pct, vehicle.driving_harshness, terrain_factor, age_years)
        wear_km_today = daily_km * wear_rate

        km_since_service += daily_km
        wear_km_since_service += wear_km_today
        days_since_service += 1
        interval_daily_kms.append(daily_km)
        interval_loads.append(load_utilization_pct)
        interval_harsh_counts.append(harsh_events_today)

        # Snapshot: what we'd know TODAY. actual_km_remaining is
        # backfilled once this interval closes (below), the same way
        # the ETA simulator derives hindsight labels.
        records.append({
            "vehicle_id": vehicle.vehicle_id,
            "lane_id": vehicle.primary_lane_id,
            "terrain_factor": terrain_factor,
            "vehicle_age_years": round(age_years, 2),
            "km_since_last_service": round(km_since_service, 1),
            "days_since_last_service": days_since_service,
            "avg_daily_km_this_interval": round(sum(interval_daily_kms) / len(interval_daily_kms), 1),
            "avg_load_utilization_pct": round(sum(interval_loads) / len(interval_loads), 1),
            "harsh_events_per_1000km": round(
                1000.0 * sum(interval_harsh_counts) / max(km_since_service, 1.0), 3
            ),
        })

        day += 1
        age_years += 1.0 / 365.0

        if wear_km_since_service >= BASE_INTERVAL_KM:
            # Service interval closes -- backfill actual_km_remaining
            # for every snapshot recorded during this interval (direct
            # index slice, not string matching), then reset.
            final_km_since_service = km_since_service
            for rec in records[interval_start_idx:]:
                actual_remaining = round(final_km_since_service - rec["km_since_last_service"], 1)
                naive_remaining = round(BASE_INTERVAL_KM - rec["km_since_last_service"], 1)
                rec["naive_km_remaining"] = naive_remaining
                rec["actual_km_remaining"] = actual_remaining
                rec["drift_km"] = round(actual_remaining - naive_remaining, 1)

            interval_start_idx = len(records)
            km_since_service = 0.0
            wear_km_since_service = 0.0
            days_since_service = 0
            interval_daily_kms = []
            interval_loads = []
            interval_harsh_counts = []

    # Drop any trailing snapshots from an interval that never closed
    # within the simulation window (no ground truth available for them).
    return [r for r in records if "actual_km_remaining" in r]


def generate_dataset(n_vehicles: int = 150, seed: int = 42) -> List[dict]:
    rng = np.random.default_rng(seed)
    all_records = []
    for i in range(n_vehicles):
        vehicle = _make_vehicle(i, rng)
        all_records.extend(simulate_vehicle(vehicle, rng))
    return all_records


def main():
    parser = argparse.ArgumentParser(description="Simulate vehicle usage histories for maintenance model training")
    parser.add_argument("--n-vehicles", type=int, default=150)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="vehicle_usage.csv")
    args = parser.parse_args()

    records = generate_dataset(n_vehicles=args.n_vehicles, seed=args.seed)

    fieldnames = list(records[0].keys())
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    n_vehicles_actual = len({r["vehicle_id"] for r in records})
    print(f"Simulated {n_vehicles_actual} vehicles -> {len(records)} usage snapshots")
    print(f"Saved to: {args.out}")

    import statistics
    naive_remaining = [BASE_INTERVAL_KM - r["km_since_last_service"] for r in records]
    actual_remaining = [r["actual_km_remaining"] for r in records]
    drift = [a - n for a, n in zip(actual_remaining, naive_remaining)]
    print(f"\nNaive rule drift (actual - naive 'every {BASE_INTERVAL_KM:.0f}km' estimate):")
    print(f"  mean: {statistics.mean(drift):.1f} km")
    print(f"  mean abs drift: {statistics.mean(abs(d) for d in drift):.1f} km")


if __name__ == "__main__":
    main()
