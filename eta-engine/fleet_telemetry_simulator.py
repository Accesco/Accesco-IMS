"""
fleet_telemetry_simulator.py
-----------------------------
Generates synthetic truck telemetry for the TMS ETA-drift model.

Per the blueprint's Carrier Telematics Integration (4B): a real system
receives a stream of (shipment_id, timestamp, lat/long, instantaneous
speed) pings and must estimate arrival time from them. There's no real
telemetry feed yet, so this simulates one: for each shipment, we run
the *entire* trip forward (so the true outcome is known), then emit
telemetry snapshots along the way -- exactly how you'd derive training
labels from a history of completed real trips ("we now know this trip
actually took 460 minutes; here's what our telemetry showed at each
10-minute mark along the way").

Speed at any moment is shaped by three independent, stackable effects,
so the naive "distance remaining / current speed" ETA is a systematically
biased estimator in predictable ways -- which is exactly what the ML
drift model is meant to learn and correct for:
  1. Carrier tendency: a carrier's on_time_score biases their typical
     cruising speed within the lane's free-flow range (better-scoring
     carriers run closer to the lane ceiling, with less variance).
  2. Time-of-day congestion: speed is reduced during rush windows
     (7-10am, 5-8pm) for the first/last ~90 minutes of a trip (proxy
     for urban congestion near origin/destination; open highway in
     between is unaffected).
  3. Random incidents: a small per-shipment chance of a slowdown
     event (breakdown, weather, accident) partway through the trip,
     causing a temporary large speed drop.

Usage:
    python fleet_telemetry_simulator.py --n-shipments 400 --seed 42
"""

import argparse
import csv
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from fleet_lanes import LANES, CARRIERS, Lane, Carrier

DT_MIN = 10.0  # simulation step size, minutes (matches a plausible GPS ping interval)
MIN_SPEED_KMPH = 5.0  # floor, so naive ETA math never divides by ~0

RUSH_WINDOWS = [(7.0, 10.0), (17.0, 20.0)]  # hour-of-day ranges
RUSH_SPEED_MULTIPLIER = 0.55  # congestion slowdown during rush + near origin/destination
RUSH_AFFECTED_MINUTES = 90.0  # only first/last N minutes of trip feel urban congestion

INCIDENT_PROBABILITY = 0.12  # chance a given shipment has one slowdown event
INCIDENT_SPEED_MULTIPLIER_RANGE = (0.25, 0.5)
INCIDENT_DURATION_MIN_RANGE = (30.0, 120.0)

SPEED_NOISE_STD_KMPH = 4.0  # per-tick sensor/driving noise


@dataclass
class Shipment:
    shipment_id: str
    lane: Lane
    carrier: Carrier
    departure_hour_of_day: float  # 0-24, wraps
    base_speed_kmph: float        # this shipment's personal cruising speed, pre-effects
    incident_start_min: Optional[float] = None
    incident_end_min: Optional[float] = None
    incident_multiplier: Optional[float] = None


def _is_rush_hour(hour_of_day: float) -> bool:
    h = hour_of_day % 24.0
    return any(start <= h < end for start, end in RUSH_WINDOWS)


def _make_shipment(idx: int, rng: np.random.Generator) -> Shipment:
    lane = LANES[rng.integers(0, len(LANES))]
    carrier = CARRIERS[rng.integers(0, len(CARRIERS))]

    # Carrier on_time_score biases where in the lane's free-flow range
    # this shipment tends to cruise: a 0.95-score carrier centers near
    # the top of the range with tight variance; a 0.78-score carrier
    # centers lower with wider variance.
    span = lane.free_flow_speed_max - lane.free_flow_speed_min
    center = lane.free_flow_speed_min + span * (0.35 + 0.6 * carrier.on_time_score)
    spread = span * (0.25 - 0.15 * carrier.on_time_score)  # weaker carriers vary more
    base_speed = float(np.clip(rng.normal(center, max(spread, 1.0)),
                                lane.free_flow_speed_min * 0.7, lane.free_flow_speed_max))

    departure_hour = float(rng.uniform(0, 24))

    shipment = Shipment(
        shipment_id=f"SHIP-{idx:05d}",
        lane=lane,
        carrier=carrier,
        departure_hour_of_day=departure_hour,
        base_speed_kmph=base_speed,
    )

    if rng.random() < INCIDENT_PROBABILITY:
        # Rough estimate of trip duration to place the incident somewhere
        # in the middle of the trip (not right at start/end).
        rough_duration_min = (lane.distance_km / base_speed) * 60.0
        start = float(rng.uniform(0.2, 0.7) * rough_duration_min)
        duration = float(rng.uniform(*INCIDENT_DURATION_MIN_RANGE))
        shipment.incident_start_min = start
        shipment.incident_end_min = start + duration
        shipment.incident_multiplier = float(rng.uniform(*INCIDENT_SPEED_MULTIPLIER_RANGE))

    return shipment


def _instantaneous_speed(shipment: Shipment, elapsed_min: float, distance_so_far: float,
                          rough_total_min: float, rng: np.random.Generator) -> float:
    speed = shipment.base_speed_kmph

    current_hour = (shipment.departure_hour_of_day + elapsed_min / 60.0) % 24.0
    near_origin = elapsed_min <= RUSH_AFFECTED_MINUTES
    near_destination = (rough_total_min - elapsed_min) <= RUSH_AFFECTED_MINUTES
    if _is_rush_hour(current_hour) and (near_origin or near_destination):
        speed *= RUSH_SPEED_MULTIPLIER

    if (shipment.incident_start_min is not None
            and shipment.incident_start_min <= elapsed_min <= shipment.incident_end_min):
        speed *= shipment.incident_multiplier

    speed += rng.normal(0, SPEED_NOISE_STD_KMPH)
    return max(speed, MIN_SPEED_KMPH)


def simulate_shipment_telemetry(shipment: Shipment, rng: np.random.Generator) -> List[dict]:
    """
    Runs the full trip forward at DT_MIN resolution, then returns one
    telemetry-tick record per step with both the "known at the time"
    features and the ground-truth actual_remaining_min (only knowable
    in hindsight, once the full trip is simulated).
    """
    lane = shipment.lane
    rough_total_min = (lane.distance_km / shipment.base_speed_kmph) * 60.0

    ticks = []  # (elapsed_min, distance_so_far, speed)
    elapsed_min = 0.0
    distance_so_far = 0.0

    while distance_so_far < lane.distance_km:
        speed = _instantaneous_speed(shipment, elapsed_min, distance_so_far, rough_total_min, rng)
        ticks.append((elapsed_min, distance_so_far, speed))
        distance_so_far += speed * (DT_MIN / 60.0)
        elapsed_min += DT_MIN

    total_duration_min = elapsed_min  # trip complete once distance_so_far >= lane.distance_km

    records = []
    for elapsed, dist_so_far, speed in ticks:
        distance_remaining = max(lane.distance_km - dist_so_far, 0.0)
        avg_speed_so_far = (dist_so_far / elapsed * 60.0) if elapsed > 0 else speed
        naive_eta_remaining_min = (distance_remaining / speed) * 60.0
        actual_remaining_min = total_duration_min - elapsed

        records.append({
            "shipment_id": shipment.shipment_id,
            "lane_id": lane.lane_id,
            "carrier_id": shipment.carrier.carrier_id,
            "carrier_on_time_score": shipment.carrier.on_time_score,
            "elapsed_min": round(elapsed, 2),
            "hour_of_day": round((shipment.departure_hour_of_day + elapsed / 60.0) % 24.0, 3),
            "is_rush_hour": _is_rush_hour((shipment.departure_hour_of_day + elapsed / 60.0) % 24.0),
            "distance_total_km": lane.distance_km,
            "distance_so_far_km": round(dist_so_far, 3),
            "distance_remaining_km": round(distance_remaining, 3),
            "progress_fraction": round(dist_so_far / lane.distance_km, 4),
            "current_speed_kmh": round(speed, 2),
            "avg_speed_so_far_kmh": round(avg_speed_so_far, 2),
            "naive_eta_remaining_min": round(naive_eta_remaining_min, 2),
            "actual_remaining_min": round(actual_remaining_min, 2),
            "drift_min": round(actual_remaining_min - naive_eta_remaining_min, 2),
            "total_duration_min": round(total_duration_min, 2),
        })

    return records


def generate_dataset(n_shipments: int = 400, seed: int = 42) -> List[dict]:
    rng = np.random.default_rng(seed)
    all_records = []
    for i in range(n_shipments):
        shipment = _make_shipment(i, rng)
        all_records.extend(simulate_shipment_telemetry(shipment, rng))
    return all_records


def main():
    parser = argparse.ArgumentParser(description="Simulate truck telemetry for ETA drift model training")
    parser.add_argument("--n-shipments", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", default="fleet_telemetry.csv")
    args = parser.parse_args()

    records = generate_dataset(n_shipments=args.n_shipments, seed=args.seed)

    fieldnames = list(records[0].keys())
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    n_shipments_actual = len({r["shipment_id"] for r in records})
    print(f"Simulated {n_shipments_actual} shipments -> {len(records)} telemetry ticks")
    print(f"Saved to: {args.out}")

    import statistics
    drifts = [r["drift_min"] for r in records]
    print(f"\nNaive ETA drift (actual - naive), across all ticks:")
    print(f"  mean: {statistics.mean(drifts):.2f} min")
    print(f"  stdev: {statistics.stdev(drifts):.2f} min")
    print(f"  mean abs drift: {statistics.mean(abs(d) for d in drifts):.2f} min")


if __name__ == "__main__":
    main()
