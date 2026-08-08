"""
Vehicle load utilization / consolidation engine.

Implements the blueprint's Capacity Optimization & Consolidation
Matrix (section 3):
  1. Constraint Sorting  -- orders sorted by mass/volume within lane
  2. Capacity Evaluation -- packed against 18,000 kg / 60 CBM ceiling
  3. Route Sequential Mapping -- orders in the same lane batched into
     one multi-stop sequence, ordered by delivery deadline
  4. Asset Provisioning -- a new truck opens whenever no existing one
     can fit the next order without breaching capacity

This is a deterministic combinatorial algorithm (First-Fit-Decreasing
bin packing), not a trained model -- runs in milliseconds, embedded
directly in this module rather than split into a separate inference
service the way app/modules/eta is (see chat history: that split
exists for eta because it's a genuine trained ML artifact matching
the replenishment-engine precedent; this isn't, so it doesn't need
the same treatment).
"""

from dataclasses import dataclass, field
from typing import List, Dict

MAX_WEIGHT_KG = 18000.0
MAX_VOLUME_CBM = 60.0


@dataclass
class ConsolidationOrder:
    order_ref: str
    lane_id: str
    weight_kg: float
    volume_cbm: float
    deadline_hour: float


@dataclass
class TruckLoad:
    truck_id: str
    lane_id: str
    orders: List[ConsolidationOrder] = field(default_factory=list)

    @property
    def total_weight_kg(self) -> float:
        return sum(o.weight_kg for o in self.orders)

    @property
    def total_volume_cbm(self) -> float:
        return sum(o.volume_cbm for o in self.orders)

    @property
    def weight_utilization_pct(self) -> float:
        return round(100.0 * self.total_weight_kg / MAX_WEIGHT_KG, 2)

    @property
    def volume_utilization_pct(self) -> float:
        return round(100.0 * self.total_volume_cbm / MAX_VOLUME_CBM, 2)

    @property
    def binding_constraint(self) -> str:
        return "weight" if self.weight_utilization_pct >= self.volume_utilization_pct else "volume"

    def can_fit(self, order: ConsolidationOrder) -> bool:
        return (
            self.total_weight_kg + order.weight_kg <= MAX_WEIGHT_KG
            and self.total_volume_cbm + order.volume_cbm <= MAX_VOLUME_CBM
        )

    def add(self, order: ConsolidationOrder):
        self.orders.append(order)

    def stops_by_deadline(self) -> List[ConsolidationOrder]:
        return sorted(self.orders, key=lambda o: o.deadline_hour)


def _ffd_key(order: ConsolidationOrder) -> float:
    """First-Fit-Decreasing sort key: pack the "heaviest footprint"
    orders first, where footprint is whichever constraint (weight or
    volume) the order consumes a larger fraction of."""
    return max(order.weight_kg / MAX_WEIGHT_KG, order.volume_cbm / MAX_VOLUME_CBM)


def consolidate_orders(orders: List[ConsolidationOrder]) -> Dict[str, object]:
    """Groups orders by lane, then runs FFD bin-packing within each
    lane. Returns loads + any orders too large to ever fit a truck
    (flagged, not silently mispacked)."""
    by_lane: Dict[str, List[ConsolidationOrder]] = {}
    for o in orders:
        by_lane.setdefault(o.lane_id, []).append(o)

    all_loads: List[TruckLoad] = []
    oversized: List[ConsolidationOrder] = []

    for lane_id, lane_orders in by_lane.items():
        placeable = []
        for o in lane_orders:
            if o.weight_kg > MAX_WEIGHT_KG or o.volume_cbm > MAX_VOLUME_CBM:
                oversized.append(o)
            else:
                placeable.append(o)

        placeable.sort(key=_ffd_key, reverse=True)

        lane_trucks: List[TruckLoad] = []
        truck_counter = 0
        for order in placeable:
            placed = False
            for truck in lane_trucks:
                if truck.can_fit(order):
                    truck.add(order)
                    placed = True
                    break
            if not placed:
                truck_counter += 1
                new_truck = TruckLoad(
                    truck_id=f"TRUCK-{lane_id}-{truck_counter:03d}",
                    lane_id=lane_id,
                )
                new_truck.add(order)
                lane_trucks.append(new_truck)

        all_loads.extend(lane_trucks)

    return {"loads": all_loads, "oversized_orders": oversized}
