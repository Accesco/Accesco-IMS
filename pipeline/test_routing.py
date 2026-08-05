"""
test_routing.py
----------------
Targeted test for optimize_route()'s fallback path.

BATCH_TARGET_MAX = 6, so in normal pipeline operation optimize_route()
is only ever called with n <= 6 orders -- the exact brute-force branch
(n <= 7) always fires, and the nearest-neighbor + 2-opt fallback for
n > 7 is dead code that has never actually executed. This test forces
that branch directly (bypassing the pipeline / batch-size cap
entirely) so it's verified at least once, in case BATCH_TARGET_MAX is
ever raised above 7 in the future (e.g. larger vehicles / e-cycles).

Checks:
  1. The NN+2-opt branch actually runs for n > 7 (not the brute-force
     branch) -- confirmed by monkeypatching to detect which helper
     functions get called.
  2. The returned route is a valid permutation (visits every order
     exactly once).
  3. The returned distance matches the route reconstructed from the
     index list (internal consistency).
  4. The heuristic result is "reasonable": within a generous bound of
     the brute-force-optimal distance for the same points (brute force
     is only used here as a ground-truth oracle for the test, not
     asserting the pipeline would ever call it at this size).
"""

import itertools

from geo_utils import DarkStore, haversine_km
import batching_engine as be
from batching_engine import optimize_route, _route_distance_km


class FakeOrder:
    def __init__(self, order_id, lat, lon):
        self.order_id = order_id
        self.lat = lat
        self.lon = lon


def _brute_force_optimal(store, orders):
    n = len(orders)
    best_dist = float("inf")
    for perm in itertools.permutations(range(n)):
        d = _route_distance_km(store, orders, list(perm))
        if d < best_dist:
            best_dist = d
    return best_dist


def test_fallback_branch_actually_used_for_n_gt_7(monkeypatch):
    """Confirm the NN+2-opt helpers are called (not brute-force) once
    n > 7, i.e. the fallback branch condition is correctly wired."""
    store = DarkStore(name="test_store", lat=12.9250, lon=77.6850)
    orders = [
        FakeOrder(f"ORD{i}", 12.9250 + 0.01 * i, 77.6850 + 0.007 * ((-1) ** i) * i)
        for i in range(1, 9)  # n = 8 > 7
    ]

    calls = {"nn": 0, "two_opt": 0}
    orig_nn = be._nearest_neighbor_route
    orig_2opt = be._two_opt

    def spy_nn(*args, **kwargs):
        calls["nn"] += 1
        return orig_nn(*args, **kwargs)

    def spy_2opt(*args, **kwargs):
        calls["two_opt"] += 1
        return orig_2opt(*args, **kwargs)

    monkeypatch.setattr(be, "_nearest_neighbor_route", spy_nn)
    monkeypatch.setattr(be, "_two_opt", spy_2opt)

    route, dist = optimize_route(store, orders)

    assert calls["nn"] == 1, "expected nearest-neighbor construction to run exactly once for n=8"
    assert calls["two_opt"] == 1, "expected 2-opt refinement to run exactly once for n=8"
    assert len(orders) == 8

    # 1. valid permutation: every order visited exactly once
    assert sorted(route) == list(range(len(orders)))

    # 2. distance matches reconstruction from the returned route
    reconstructed = _route_distance_km(store, orders, route)
    assert abs(reconstructed - dist) < 1e-9

    # 3. heuristic is "reasonable" vs. brute-force-optimal ground truth
    #    (generous bound -- NN+2-opt on 8 well-separated points is
    #    typically within a few % of optimal, but this is just a
    #    smoke test, not a tightness guarantee)
    optimal = _brute_force_optimal(store, orders)
    assert dist <= optimal * 1.25, (
        f"heuristic route ({dist:.4f} km) is more than 25% worse than "
        f"brute-force optimal ({optimal:.4f} km) -- investigate 2-opt"
    )


def test_exact_branch_used_for_n_lte_7(monkeypatch):
    """Sanity-check the boundary: n<=7 must NOT touch the fallback
    helpers at all (guards against the branch condition drifting)."""
    store = DarkStore(name="test_store", lat=12.9250, lon=77.6850)
    orders = [
        FakeOrder(f"ORD{i}", 12.9250 + 0.01 * i, 77.6850 + 0.006 * i)
        for i in range(1, 7)  # n = 6, matches real BATCH_TARGET_MAX
    ]

    called = {"any": False}

    def fail_if_called(*args, **kwargs):
        called["any"] = True
        raise AssertionError("fallback helper should not be called for n<=7")

    monkeypatch.setattr(be, "_nearest_neighbor_route", fail_if_called)
    monkeypatch.setattr(be, "_two_opt", fail_if_called)

    route, dist = optimize_route(store, orders)

    assert not called["any"]
    assert sorted(route) == list(range(len(orders)))

    # brute-force branch must be exactly optimal
    optimal = _brute_force_optimal(store, orders)
    assert abs(dist - optimal) < 1e-9
