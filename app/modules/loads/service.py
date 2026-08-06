from typing import List

from app.modules.loads.consolidation_engine import (
    ConsolidationOrder,
    TruckLoad,
    consolidate_orders,
)
from app.modules.loads.schemas import (
    ERPOrderInput,
    ConsolidationResponse,
    ConsolidationSummary,
    TruckLoadResponse,
)


class LoadConsolidationService:
    """Stateless -- computes a consolidation plan and returns it.
    Nothing persisted (see chat: an ETA-style history log didn't apply
    here since the person decided this stays ephemeral for now)."""

    def consolidate(self, orders_in: List[ERPOrderInput]) -> ConsolidationResponse:
        orders = [
            ConsolidationOrder(
                order_ref=o.order_ref,
                lane_id=o.lane_id,
                weight_kg=o.weight_kg,
                volume_cbm=o.volume_cbm,
                deadline_hour=o.deadline_hour,
            )
            for o in orders_in
        ]

        result = consolidate_orders(orders)
        loads: List[TruckLoad] = result["loads"]
        oversized: List[ConsolidationOrder] = result["oversized_orders"]

        load_responses = [
            TruckLoadResponse(
                truck_id=load.truck_id,
                lane_id=load.lane_id,
                n_orders=len(load.orders),
                total_weight_kg=round(load.total_weight_kg, 1),
                total_volume_cbm=round(load.total_volume_cbm, 2),
                weight_utilization_pct=load.weight_utilization_pct,
                volume_utilization_pct=load.volume_utilization_pct,
                binding_constraint=load.binding_constraint,
                order_refs_by_deadline=[o.order_ref for o in load.stops_by_deadline()],
            )
            for load in loads
        ]

        binding = [l.binding_constraint for l in loads]
        summary = ConsolidationSummary(
            n_orders_input=len(orders_in),
            n_orders_packed=sum(len(l.orders) for l in loads),
            n_oversized_orders=len(oversized),
            n_trucks=len(loads),
            avg_weight_utilization_pct=(
                round(sum(l.weight_utilization_pct for l in loads) / len(loads), 2) if loads else None
            ),
            avg_volume_utilization_pct=(
                round(sum(l.volume_utilization_pct for l in loads) / len(loads), 2) if loads else None
            ),
            trucks_binding_on_weight=sum(1 for b in binding if b == "weight"),
            trucks_binding_on_volume=sum(1 for b in binding if b == "volume"),
        )

        return ConsolidationResponse(
            summary=summary,
            loads=load_responses,
            oversized_order_refs=[o.order_ref for o in oversized],
        )
