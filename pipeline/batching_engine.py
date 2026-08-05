"""
batching_engine.py
--------------------
The core pipeline: takes a stream of Orders and produces Batches,
one rider per batch, one vertical per rider per dispatch cycle.

Pipeline stages
---------------
1. SPLIT   — route each order to its vertical (NE/NW/SE/SW) queue,
             separately for each delivery mode (instant_10 / scheduled_25),
             since the two SLAs need different batching windows.
2. WINDOW  — accumulate orders in a rolling time window per
             (vertical, mode) queue. A window closes (triggers batching)
             when it hits the target batch size (5-6) OR its max wait
             time elapses (whichever comes first).
3. ROUTE   — for orders in a closed window, solve a small TSP
             (nearest-neighbor construction + 2-opt improvement) rooted
             at the dark store, to minimize the rider's total travel
             distance across the batch.
4. ASSIGN  — assign the routed batch to a rider. A rider is dedicated
             to one vertical for the batch's duration (never crosses
             into another vertical mid-batch).
5. SCORE   — estimate whether the batch's route time fits inside the
             delivery mode's SLA, using an average urban 2-wheeler speed.
"""

import heapq
import itertools
from dataclasses import dataclass, field
from typing import List, Dict

from geo_utils import DarkStore, haversine_km, VERTICALS

# --- Tunable pipeline parameters -------------------------------------------

BATCH_TARGET_MIN = 5
BATCH_TARGET_MAX = 6

# Max time (minutes) a queue will wait to fill a batch before dispatching
# whatever it has (if at least MIN_VIABLE_BATCH orders are present).
MAX_WAIT_MIN = {
    # Worked backwards from the SLA budget: prep (2 min) + worst-case
    # corner-of-quadrant travel at 22 km/h (~6 min for a ~2.2 km diagonal)
    # already consumes ~8 of the 10-min SLA, so only ~2 min can go to
    # waiting for more orders to join the batch.
    "instant_10": 2.0,
    # 25-min SLA has far more slack: prep + worst-case travel at
    # 18 km/h (~7.3 min) leaves ~15 min of safe accumulation time.
    "scheduled_25": 15.0,
}
# NOTE: there is intentionally no minimum viable batch size gate here.
# Once a queue's deadline is reached, we dispatch whatever is pending
# -- even a single order -- rather than risk breaching its SLA by
# waiting for more orders to join. Batch size is always secondary to
# the delivery-time promise.

RIDER_SPEED_KMPH = {
    "instant_10": 22.0,     # bikes, prioritized lanes/appointments
    "scheduled_25": 18.0,   # standard urban 2-wheeler speed w/ traffic
}
PREP_TIME_MIN = 2.0  # picking + packing time at the dark store before departure


@dataclass
class Batch:
    batch_id: str
    vertical: str
    delivery_mode: str
    order_ids: List[str]
    route_order_ids: List[str]      # order_ids in optimized visiting sequence
    route_km: float
    est_delivery_min: float         # prep + travel time for full batch
    sla_min: int
    sla_met: bool
    rider_id: str
    dispatch_min: float             # simulation-time the batch left the store
    is_new_rider: bool              # True if this trip minted a fresh rider_id
                                     # rather than reusing one returning to store
    rider_returns_at: float         # sim-time this trip's rider is free again
                                     # (dispatch_min + forward route + return leg)


def _route_distance_km(store: DarkStore, orders, order_seq: List[int]) -> float:
    """Total distance store -> orders in order_seq order (no return leg)."""
    pts = [(store.lat, store.lon)] + [(orders[i].lat, orders[i].lon) for i in order_seq]
    return sum(
        haversine_km(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
        for i in range(len(pts) - 1)
    )


def _nearest_neighbor_route(store: DarkStore, orders) -> List[int]:
    """Greedy nearest-neighbor construction, starting from the store."""
    remaining = list(range(len(orders)))
    route = []
    cur_lat, cur_lon = store.lat, store.lon
    while remaining:
        nxt = min(remaining, key=lambda i: haversine_km(cur_lat, cur_lon, orders[i].lat, orders[i].lon))
        route.append(nxt)
        remaining.remove(nxt)
        cur_lat, cur_lon = orders[nxt].lat, orders[nxt].lon
    return route


def _two_opt(store: DarkStore, orders, route: List[int]) -> List[int]:
    """Classic 2-opt local search to shave distance off the NN route."""
    best = route[:]
    best_dist = _route_distance_km(store, orders, best)
    improved = True
    while improved:
        improved = False
        for i in range(len(best) - 1):
            for j in range(i + 1, len(best)):
                candidate = best[:i] + best[i:j + 1][::-1] + best[j + 1:]
                d = _route_distance_km(store, orders, candidate)
                if d < best_dist - 1e-9:
                    best, best_dist = candidate, d
                    improved = True
        # loop again if any improvement was found in the full pass
    return best


def optimize_route(store: DarkStore, batch_orders) -> (List[int], float):
    """
    Solve a small TSP for a batch of 5-6 orders: nearest-neighbor
    construction + 2-opt refinement, minimizing total rider travel
    distance from the dark store through every drop.
    Exact brute-force is used instead for batches of size <=7 for a
    guaranteed-optimal route (cheap at this size); falls back to the
    heuristic above for anything larger.
    """
    n = len(batch_orders)
    if n <= 7:
        best_perm, best_dist = None, float("inf")
        for perm in itertools.permutations(range(n)):
            d = _route_distance_km(store, batch_orders, list(perm))
            if d < best_dist:
                best_dist, best_perm = d, list(perm)
        return best_perm, best_dist

    nn_route = _nearest_neighbor_route(store, batch_orders)
    opt_route = _two_opt(store, batch_orders, nn_route)
    return opt_route, _route_distance_km(store, batch_orders, opt_route)


class RiderPool:
    """
    Manages rider reuse within a single vertical (riders are locked to
    one vertical per the spec, so pools don't share riders across
    verticals -- see chat for the tradeoff vs. a global pool).

    A rider becomes available again `dispatch_min + forward route time
    + return-to-store time` after being sent out, and is reused for
    the vertical's next trip rather than minting a fresh rider every
    single dispatch. This is the standard greedy for the "minimum
    concurrent resources for overlapping intervals" problem
    (equivalent to minimum-meeting-rooms): always hand out the
    earliest-freed rider first. That greedy is provably optimal for
    minimizing the distinct-rider count needed for a given trip
    schedule, so distinct rider_ids minted == the actual fleet size
    required for this vertical's pattern of dispatches -- not a trip
    counter mislabeled as headcount.
    """

    def __init__(self, vertical: str):
        self.vertical = vertical
        self._counter = 0
        self._available: List[tuple] = []  # min-heap of (free_at, rider_id)

    def acquire(self, now_min: float):
        """Return (rider_id, is_new). Reuses the earliest-freed rider
        if one is available by now_min; otherwise mints a new one."""
        if self._available and self._available[0][0] <= now_min + 1e-9:
            _, rider_id = heapq.heappop(self._available)
            return rider_id, False
        self._counter += 1
        rider_id = f"RIDER-{self.vertical}-{self._counter:03d}"
        return rider_id, True

    def release(self, rider_id: str, free_at: float):
        heapq.heappush(self._available, (free_at, rider_id))

    @property
    def fleet_size(self) -> int:
        """Total distinct riders ever minted for this vertical -- the
        real headcount this vertical's demand pattern required."""
        return self._counter


class VerticalQueue:
    """Rolling buffer of pending orders for one (vertical, mode) pair."""

    def __init__(self, vertical: str, mode: str):
        self.vertical = vertical
        self.mode = mode
        self.pending: List = []
        self.window_start: float = None

    def add(self, order):
        if not self.pending:
            self.window_start = order.arrival_min
        self.pending.append(order)

    def ready(self, now_min: float) -> bool:
        if not self.pending:
            return False
        if len(self.pending) >= BATCH_TARGET_MAX:
            return True
        # Deadline-protection: once the oldest order in this queue has
        # waited MAX_WAIT_MIN, dispatch whatever is pending -- even a
        # single order -- rather than risk breaching its SLA. Batch size
        # is a secondary objective to the delivery-time promise.
        elapsed = now_min - self.window_start
        # Epsilon guards against float rounding: a deadline event
        # scheduled for exactly window_start + MAX_WAIT_MIN can pop
        # with elapsed computed as e.g. 1.9999999996 instead of 2.0,
        # which would fail this check, reschedule an identical
        # deadline, and loop forever without advancing time.
        if elapsed >= MAX_WAIT_MIN[self.mode] - 1e-9:
            return True
        return False

    def pop_batch(self):
        batch = self.pending[:BATCH_TARGET_MAX]
        self.pending = self.pending[BATCH_TARGET_MAX:]
        self.window_start = self.pending[0].arrival_min if self.pending else None
        return batch


class BatchingPipeline:
    """
    Orchestrates SPLIT -> WINDOW -> ROUTE -> ASSIGN -> SCORE across all
    4 verticals x 2 delivery modes for a single dark store.
    """

    def __init__(self, store: DarkStore):
        self.store = store
        self.queues: Dict[str, VerticalQueue] = {
            f"{v}|{m}": VerticalQueue(v, m)
            for v in VERTICALS
            for m in ("instant_10", "scheduled_25")
        }
        self.batches: List[Batch] = []
        self._rider_pools: Dict[str, RiderPool] = {v: RiderPool(v) for v in VERTICALS}
        self._batch_counter = 0

    def _dispatch(self, queue: VerticalQueue, now_min: float):
        batch_orders = queue.pop_batch()
        route_idx, route_km = optimize_route(self.store, batch_orders)

        # SLA is measured per-order from THAT order's own arrival time:
        # wait-in-queue + prep + cumulative travel time to reach it in
        # the route sequence -- not just the batch's total travel time.
        # The last stop on the route is the one most at risk of breach.
        sla_min = batch_orders[0].sla_min
        worst_case_min = 0.0
        cum_travel = 0.0
        pts = [(self.store.lat, self.store.lon)] + [
            (batch_orders[i].lat, batch_orders[i].lon) for i in route_idx
        ]
        for pos, i in enumerate(route_idx):
            leg_km = haversine_km(pts[pos][0], pts[pos][1], pts[pos + 1][0], pts[pos + 1][1])
            cum_travel += (leg_km / RIDER_SPEED_KMPH[queue.mode]) * 60.0
            wait_min = now_min - batch_orders[i].arrival_min
            order_total_min = wait_min + PREP_TIME_MIN + cum_travel
            worst_case_min = max(worst_case_min, order_total_min)

        # Return leg: direct distance from the last stop back to the
        # store, at the same average-speed assumption as the outbound
        # route (no separate "empty return" speed modeled yet).
        last_lat, last_lon = pts[-1]
        return_km = haversine_km(last_lat, last_lon, self.store.lat, self.store.lon)
        return_min = (return_km / RIDER_SPEED_KMPH[queue.mode]) * 60.0
        # Rider is busy from dispatch through prep + full route + return.
        rider_returns_at = now_min + PREP_TIME_MIN + cum_travel + return_min

        pool = self._rider_pools[queue.vertical]
        rider_id, is_new = pool.acquire(now_min)
        pool.release(rider_id, rider_returns_at)

        self._batch_counter += 1
        batch = Batch(
            batch_id=f"BATCH-{self._batch_counter:05d}",
            vertical=queue.vertical,
            delivery_mode=queue.mode,
            order_ids=[o.order_id for o in batch_orders],
            route_order_ids=[batch_orders[i].order_id for i in route_idx],
            route_km=round(route_km, 3),
            est_delivery_min=round(worst_case_min, 2),
            sla_min=sla_min,
            sla_met=worst_case_min <= sla_min,
            rider_id=rider_id,
            dispatch_min=round(now_min, 2),
            is_new_rider=is_new,
            rider_returns_at=round(rider_returns_at, 2),
        )
        self.batches.append(batch)
        return batch

    def _maybe_schedule_deadline(self, key: str, queue: "VerticalQueue", events: list, seq):
        """Push a deadline-check event at the exact moment this queue's
        oldest pending order will breach MAX_WAIT_MIN, so dispatch
        happens at the true trigger time instead of on a polling grid."""
        if queue.pending and queue.window_start is not None:
            deadline_t = queue.window_start + MAX_WAIT_MIN[queue.mode]
            heapq.heappush(events, (deadline_t, next(seq), "deadline", key))

    def run(self, orders: List, sim_minutes: int, flush_interval: float = None):
        """
        Event-driven simulation. Two kinds of events are processed in
        exact time order via a min-heap:
          - "arrival": a new order joins its (vertical, mode) queue.
            Checked for an immediate size-triggered dispatch.
          - "deadline": the exact instant an active queue's oldest
            order would breach MAX_WAIT_MIN. Checked for a
            deadline-triggered dispatch.

        This replaces the previous fixed-tick polling loop (which
        checked readiness once per `flush_interval` minutes) with
        exact-time dispatch, removing the systematic bias where an
        order could sit past its intended wait cap for up to a full
        tick before anyone checked -- previously measured as ~0.46 min
        (23%) of overshoot on the tight 2-min instant_10 cap.

        `flush_interval` is accepted for backward-compatible call
        signatures but is no longer used (the event loop needs no
        polling grid); passing it has no effect.
        """
        seq = itertools.count()
        events = []  # heap of (time, tie_breaker, kind, payload)

        for idx, o in enumerate(orders):
            heapq.heappush(events, (o.arrival_min, next(seq), "arrival", idx))

        while events:
            t, _, kind, payload = heapq.heappop(events)
            if t > sim_minutes:
                # Heap pops in time order, so every remaining event is
                # also beyond the simulation window -- stop early and
                # let the end-of-sim flush below handle what's pending.
                break

            if kind == "arrival":
                o = orders[payload]
                key = f"{o.vertical}|{o.delivery_mode}"
                q = self.queues[key]
                was_empty = not q.pending
                q.add(o)
                if was_empty:
                    self._maybe_schedule_deadline(key, q, events, seq)
                while q.ready(t):
                    self._dispatch(q, t)
                if q.pending:
                    # A leftover remainder after a size-triggered
                    # dispatch starts a fresh window -- schedule its
                    # own deadline.
                    self._maybe_schedule_deadline(key, q, events, seq)

            elif kind == "deadline":
                key = payload
                q = self.queues[key]
                while q.ready(t):
                    self._dispatch(q, t)
                if q.pending:
                    # Queue wasn't actually at its deadline yet (a
                    # stale/duplicate event, or window_start moved) --
                    # or it's a fresh remainder. Either way, reschedule
                    # against the queue's current window_start.
                    self._maybe_schedule_deadline(key, q, events, seq)

        # end-of-sim flush: dispatch anything left over, regardless of size
        for q in self.queues.values():
            while q.pending:
                self._dispatch(q, sim_minutes)

        return self.batches
