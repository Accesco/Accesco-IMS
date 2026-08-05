"""
scenario_analysis.py
----------------------
Answers the operational question underneath the batching-pipeline
request: at what order density does a rider actually get 5-6 orders
per trip, given the 10-min / 25-min SLA constraints and a 4-way
vertical split?

Reuses demand_simulator.py's own scenario handling (conservative /
moderate / optimistic = 40 / 65 / 90 orders/day, spread across its
DEFAULT_OPERATING_HOURS window) as the launch-stage baseline, then
sweeps higher densities using the SAME daily->rate conversion formula
demand_simulator.py already uses internally -- so there's one source
of truth for "daily orders -> arrival rate," not two competing ones.

Verified against the actual batching_engine.py / simulation_runner.py:
  - BatchingPipeline(STORE) constructed with the store, .run(orders,
    sim_minutes=...) -> list[Batch]
  - simulation_runner.summarize(orders, batches) returns:
      total_orders_simulated, total_orders_batched, orders_match,
      total_batches, avg_batch_size, overall_sla_compliance_rate,
      by_mode (nested: batches/orders/avg_batch_size/sla_compliance_rate
      per delivery_mode key), by_vertical (same shape, per vertical key)
    -- NOTE: summarize() does not expose a rider count, so
    riders_deployed is computed here directly from the batch list
    (count of distinct rider_id values).
"""

import json
from collections import Counter

from demand_simulator import (
    simulate_orders,
    STORE,
    SCENARIOS,
    DEFAULT_OPERATING_HOURS,
)
from batching_engine import BatchingPipeline
from simulation_runner import summarize

# Simulate the full operating day (matches demand_simulator.py's own
# model) rather than inventing a separate peak-window fraction here.
SIM_MINUTES = int(DEFAULT_OPERATING_HOURS * 60)  # e.g. 12h -> 720 min

# Scale-up multiples beyond the report's own Optimistic case, to find
# the density breakpoint where 5-6 order batching becomes the norm.
SCALE_UP_MULTIPLIERS = [3, 6, 10, 20, 35]


def daily_orders_to_rate(daily_orders: float) -> float:
    """Identical formula to demand_simulator.simulate_orders()'s internal
    scenario->rate conversion, so a manually-specified daily_orders
    number here behaves exactly like a named scenario would."""
    return daily_orders / DEFAULT_OPERATING_HOURS / 60.0


def build_scenario_list():
    """
    Returns a list of (label, daily_orders, scenario_key_or_None, rate_or_None).
    Named scenarios pass scenario_key so demand_simulator does its own
    conversion; scale-ups pass a directly-computed rate since no named
    scenario exists above Optimistic.
    """
    rows = [
        (f"{name.capitalize()} (report Test 4)", daily, name, None)
        for name, daily in SCENARIOS.items()
    ]
    optimistic_daily = SCENARIOS["optimistic"]
    for mult in SCALE_UP_MULTIPLIERS:
        daily = optimistic_daily * mult
        rows.append((f"Scale-up {mult}x", daily, None, daily_orders_to_rate(daily)))
    return rows


def run_scenario(scenario_key: str = None, rate: float = None, seed: int = 7):
    if rate is None:
        orders = simulate_orders(sim_minutes=SIM_MINUTES, scenario=scenario_key, seed=seed)
    else:
        orders = simulate_orders(sim_minutes=SIM_MINUTES, arrival_rate_per_min=rate, seed=seed)

    pipeline = BatchingPipeline(STORE)
    batches = pipeline.run(orders, sim_minutes=SIM_MINUTES)
    metrics = summarize(orders, batches)

    # riders_deployed: summarize() doesn't expose this, so derive it
    # directly from the batch list (1 rider_id per dispatched batch,
    # but the same physical rider ID is reused across dispatch cycles
    # within a vertical, so this is "distinct rider assignments," not
    # "distinct physical riders" -- see note in the printed table).
    riders_deployed = len({b.rider_id for b in batches})

    # Extra diagnostic not in summarize(): hotspot vs background order
    # split, useful for sanity-checking that batch-size shifts are
    # coming from real density changes, not a simulator artifact.
    source_counts = Counter(getattr(o, "source", "unknown") for o in orders)

    return metrics, riders_deployed, source_counts


def main():
    rows = []
    for label, daily, scenario_key, rate in build_scenario_list():
        metrics, riders_deployed, source_counts = run_scenario(
            scenario_key=scenario_key, rate=rate
        )

        by_mode = metrics.get("by_mode", {})
        instant = by_mode.get("instant_10", {})
        scheduled = by_mode.get("scheduled_25", {})

        rows.append({
            "scenario": label,
            "daily_orders_assumed": daily,
            "window_orders": metrics.get("total_orders_simulated", 0),
            "orders_match": metrics.get("orders_match"),
            "avg_batch_size": metrics.get("avg_batch_size", 0),
            "riders_deployed": riders_deployed,
            "overall_sla_compliance_rate": metrics.get("overall_sla_compliance_rate", 0) or 0,
            "instant_10_avg_batch": instant.get("avg_batch_size", 0),
            "instant_10_sla_rate": instant.get("sla_compliance_rate", 0) or 0,
            "scheduled_25_avg_batch": scheduled.get("avg_batch_size", 0),
            "scheduled_25_sla_rate": scheduled.get("sla_compliance_rate", 0) or 0,
            "hotspot_orders": source_counts.get("hotspot", 0),
            "background_orders": source_counts.get("background", 0),
        })

    header = (f"{'Scenario':<28}{'Daily':>7}{'WinOrd':>8}{'AvgBatch':>10}"
              f"{'Instant10':>11}{'Sched25':>9}{'SLA%':>7}{'Riders':>8}")
    print(header)
    for r in rows:
        print(f"{r['scenario']:<28}{r['daily_orders_assumed']:>7}{r['window_orders']:>8}"
              f"{r['avg_batch_size']:>10}{r['instant_10_avg_batch']:>11}"
              f"{r['scheduled_25_avg_batch']:>9}{r['overall_sla_compliance_rate']*100:>6.1f}%"
              f"{r['riders_deployed']:>8}")

    bad = [r["scenario"] for r in rows if r["orders_match"] is False]
    if bad:
        print(f"\nWARNING -- orders_match was False for: {', '.join(bad)}"
              f" (possible queue leak in BatchingPipeline.run() -- see simulation_runner.summarize())")

    with open("scenario_analysis.json", "w") as f:
        json.dump(rows, f, indent=2)


if __name__ == "__main__":
    main()
