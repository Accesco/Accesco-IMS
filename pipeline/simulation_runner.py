"""
simulation_runner.py
---------------------
Single-scenario run of the batching pipeline:
  demand_simulator.simulate_orders() -> BatchingPipeline.run()
  -> orders.csv, batches.csv, metrics.json

Usage:
    python simulation_runner.py --sim-minutes 720 --rate 0.9 --seed 42
    python simulation_runner.py --sim-minutes 720 --scenario moderate --seed 42

Note: --sim-minutes defaults to 720 (DEFAULT_OPERATING_HOURS * 60, a
full 12h day), matching the whole-day model demand_simulator.py and
scenario_analysis.py both use. Pass a smaller value deliberately for a
quick spot-check window -- e.g. --sim-minutes 20 for the sanity-check
runs earlier in this project -- but note batch/SLA stats from a short
window won't represent a full day's behavior.
"""

import argparse
import csv
import json
from collections import defaultdict
from typing import List

from demand_simulator import simulate_orders, STORE, Order
from batching_engine import BatchingPipeline, Batch


# ---------------------------------------------------------------------
# Exporters
# ---------------------------------------------------------------------

def export_orders(orders: List[Order], path: str = "orders.csv"):
    """One CSV row per raw simulated order, for eyeballing demand."""
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["order_id", "lat", "lon", "vertical", "pincode", "delivery_mode",
             "sla_min", "arrival_min", "item_count"]
        )
        for o in orders:
            writer.writerow(
                [o.order_id, o.lat, o.lon, o.vertical, o.pincode, o.delivery_mode,
                 o.sla_min, round(o.arrival_min, 3), o.item_count]
            )


def export_batches(batches: List[Batch], path: str = "batches.csv"):
    """One CSV row per dispatched batch. order_ids joined with '|' since
    CSV cells can't hold lists directly."""
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["batch_id", "vertical", "delivery_mode", "rider_id", "is_new_rider",
             "order_count", "route_km", "est_delivery_min", "sla_min", "sla_met",
             "dispatch_min", "rider_returns_at", "route_order_ids"]
        )
        for b in batches:
            writer.writerow(
                [b.batch_id, b.vertical, b.delivery_mode, b.rider_id, b.is_new_rider,
                 len(b.order_ids), b.route_km, b.est_delivery_min, b.sla_min, b.sla_met,
                 b.dispatch_min, b.rider_returns_at, "|".join(b.route_order_ids)]
            )


# ---------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------

def _breakdown(batches: List[Batch], key_fn):
    """Shared helper for the by_mode / by_vertical breakdowns."""
    grouped = defaultdict(lambda: {"batches": 0, "orders": 0, "sla_met": 0})
    for b in batches:
        g = grouped[key_fn(b)]
        g["batches"] += 1
        g["orders"] += len(b.order_ids)
        g["sla_met"] += int(b.sla_met)

    out = {}
    for key, g in grouped.items():
        out[key] = {
            "batches": g["batches"],
            "orders": g["orders"],
            "avg_batch_size": round(g["orders"] / g["batches"], 3) if g["batches"] else 0.0,
            "sla_compliance_rate": round(g["sla_met"] / g["batches"], 4) if g["batches"] else None,
        }
    return out


def summarize(orders: List[Order], batches: List[Batch]) -> dict:
    """
    Compute pipeline-level metrics:
      - total orders simulated vs. actually batched (should match --
        a mismatch means orders got stuck in a queue and never
        dispatched, which is a bug worth catching here)
      - average batch size
      - overall SLA compliance rate
      - breakdown by delivery mode (instant vs scheduled)
      - breakdown by vertical (spot quadrants that are starved for orders)
    """
    total_orders_simulated = len(orders)
    total_orders_batched = sum(len(b.order_ids) for b in batches)
    n_batches = len(batches)

    avg_batch_size = round(total_orders_batched / n_batches, 3) if n_batches else 0.0
    sla_met_count = sum(1 for b in batches if b.sla_met)
    overall_sla_rate = round(sla_met_count / n_batches, 4) if n_batches else None

    summary = {
        "total_orders_simulated": total_orders_simulated,
        "total_orders_batched": total_orders_batched,
        "orders_match": total_orders_simulated == total_orders_batched,
        "total_batches": n_batches,
        "avg_batch_size": avg_batch_size,
        "overall_sla_compliance_rate": overall_sla_rate,
        "by_mode": _breakdown(batches, lambda b: b.delivery_mode),
        "by_vertical": _breakdown(batches, lambda b: b.vertical),
    }

    if not summary["orders_match"]:
        # Flag loudly -- this indicates a queue leak (orders never
        # dispatched by end-of-sim flush). See Step 2 stress tests.
        summary["WARNING"] = (
            f"total_orders_simulated ({total_orders_simulated}) != "
            f"total_orders_batched ({total_orders_batched}) -- "
            f"check for a queue leak in BatchingPipeline.run()"
        )

    return summary


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Run one batching pipeline simulation")
    parser.add_argument("--sim-minutes", type=int, default=720,
                         help="Simulation window length in minutes (default: 720 = full 12h day)")
    parser.add_argument("--rate", type=float, default=None,
                         help="Order arrival rate per minute (overrides --scenario if given)")
    parser.add_argument("--scenario", default="moderate",
                         choices=["conservative", "moderate", "optimistic"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--orders-out", default="orders.csv")
    parser.add_argument("--batches-out", default="batches.csv")
    parser.add_argument("--metrics-out", default="metrics.json")
    args = parser.parse_args()

    orders = simulate_orders(
        sim_minutes=args.sim_minutes,
        arrival_rate_per_min=args.rate,
        scenario=args.scenario,
        seed=args.seed,
    )

    pipeline = BatchingPipeline(STORE)
    batches = pipeline.run(orders, sim_minutes=args.sim_minutes)

    export_orders(orders, args.orders_out)
    export_batches(batches, args.batches_out)

    summary = summarize(orders, batches)
    with open(args.metrics_out, "w") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
