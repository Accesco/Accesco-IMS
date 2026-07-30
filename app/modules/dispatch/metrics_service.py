# app/modules/dispatch/metrics_service.py
"""
Accuracy metric computations for the dispatch system. Exposes live performance
against defined baseline, target, and goal thresholds.

"""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order
from app.models.batch import Batch
from app.models.rider import Rider
from app.models.community import Community
from app.models.forecast import ForecastMetric

logger = logging.getLogger("metrics_service")

# Rolling window for most metrics
ROLLING_WINDOW_HOURS = 24

# Performance thresholds: baseline (rule-based), target, and goal
ACCURACY_THRESHOLDS = {
    "assignment_accuracy": {"baseline": 0.62, "target": 0.80, "goal": 0.93},
    "batch_fill_rate":     {"baseline": 0.45, "target": 0.70, "goal": 0.82},
    "on_time_rate":        {"baseline": 0.74, "target": 0.88, "goal": 0.96},
    "forecast_mape":       {"baseline": 0.55, "target": 0.78, "goal": 0.90},
    "rider_utilisation":   {"baseline": 0.60, "target": 0.78, "goal": 0.88},
}


def _thresholds(key: str) -> Dict[str, float]:
    return ACCURACY_THRESHOLDS.get(key, {})


def _build_response(metric_key: str, current_value: Optional[float], extra: Optional[Dict] = None) -> Dict[str, Any]:
    
    t = _thresholds(metric_key)
    resp = {
        "metric": metric_key,
        "current_value": round(current_value, 4) if current_value is not None else None,
        "doc_b_baseline": t.get("baseline"),
        "doc_b_target": t.get("target"),
        "doc_b_goal": t.get("goal"),
        "window_hours": ROLLING_WINDOW_HOURS,
    }
    if extra:
        resp.update(extra)
    return resp


class MetricsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def assignment_accuracy(self) -> Dict[str, Any]:
        """
        T: Fraction of completed assignments rated 'optimal'.
        An assignment is optimal:
        rider picked up within 2 min of ready AND delivered within SLA.
        This is stored as Order.assignment_was_optimal after delivery.
        """
        since = datetime.now(timezone.utc) - timedelta(hours=ROLLING_WINDOW_HOURS)

        total_res = await self.db.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.assignment_was_optimal.isnot(None),
                    Order.actual_delivered_at >= since,
                )
            )
        )
        total = int(total_res.scalar() or 0)

        if total == 0:
            return _build_response("assignment_accuracy", None, {"note": "No completed deliveries with labels yet"})

        optimal_res = await self.db.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.assignment_was_optimal == True,
                    Order.actual_delivered_at >= since,
                )
            )
        )
        optimal_count = int(optimal_res.scalar() or 0)
        rate = optimal_count / total

        return _build_response("assignment_accuracy", rate, {"optimal_count": optimal_count, "total_labelled": total})

    async def batch_fill_rate(self) -> Dict[str, Any]:
        """
        actual_batch_size / community.max_batch_size per dispatched batch,
        rolled up as an overall average and per-community breakdown.
        """
        since = datetime.now(timezone.utc) - timedelta(hours=ROLLING_WINDOW_HOURS)

        batches_res = await self.db.execute(
            select(Batch).where(
                and_(
                    Batch.actual_batch_size.isnot(None),
                    Batch.status.in_(["ASSIGNED", "DELIVERED"]),
                )
            )
        )
        batches = batches_res.scalars().all()

        if not batches:
            return _build_response("batch_fill_rate", None, {"note": "No dispatched batches with size data yet"})

        # Load communities for max_batch_size lookup
        comm_res = await self.db.execute(select(Community))
        communities = {c.id: c for c in comm_res.scalars().all()}

        per_community: Dict[str, Dict] = {}
        fill_ratios = []

        for batch in batches:
            community = communities.get(batch.community_id)
            if not community:
                continue
            max_size = community.max_batch_size or 1
            ratio = batch.actual_batch_size / max_size
            fill_ratios.append(ratio)

            cid = batch.community_id
            if cid not in per_community:
                per_community[cid] = {"batches": 0, "fill_sum": 0.0}
            per_community[cid]["batches"] += 1
            per_community[cid]["fill_sum"] += ratio

        if not fill_ratios:
            return _build_response("batch_fill_rate", None)

        overall = sum(fill_ratios) / len(fill_ratios)
        community_breakdown = {
            cid: round(v["fill_sum"] / v["batches"], 4)
            for cid, v in per_community.items()
        }

        return _build_response(
            "batch_fill_rate",
            overall,
            {"batch_count": len(fill_ratios), "per_community": community_breakdown},
        )

    async def on_time_rate(self) -> Dict[str, Any]:
        """
        Fraction of delivered orders that met their SLA deadline.
        """
        since = datetime.now(timezone.utc) - timedelta(hours=ROLLING_WINDOW_HOURS)

        total_res = await self.db.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.status == "DELIVERED",
                    Order.actual_delivered_at >= since,
                )
            )
        )
        total = int(total_res.scalar() or 0)

        if total == 0:
            return _build_response("on_time_rate", None, {"note": "No delivered orders in window"})

        on_time_res = await self.db.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.status == "DELIVERED",
                    Order.actual_delivered_at >= since,
                    Order.actual_delivered_at <= Order.sla_deadline,
                )
            )
        )
        on_time = int(on_time_res.scalar() or 0)
        rate = on_time / total

        return _build_response("on_time_rate", rate, {"on_time_count": on_time, "total_delivered": total})

    async def forecast_mape(self) -> Dict[str, Any]:
        """
        Mean Absolute Percentage Error of the Holt-Winters demand forecaster.
        For each ForecastMetric row whose target_time has passed, compare
        predicted_orders_per_min against the actual order count in that 10-min window.
        MAPE = mean(|actual - predicted| / max(actual, epsilon)) * 100
        (inverted: accuracy = 1 - MAPE/100)
        """
        now = datetime.now(timezone.utc)
        since = now - timedelta(hours=ROLLING_WINDOW_HOURS)

        metrics_res = await self.db.execute(
            select(ForecastMetric).where(
                and_(
                    ForecastMetric.target_time >= since,
                    ForecastMetric.target_time < now,  # only past windows
                )
            )
        )
        metrics = metrics_res.scalars().all()

        if not metrics:
            return _build_response("forecast_mape", None, {"note": "No forecast metrics with elapsed windows yet"})

        ape_list = []
        for fm in metrics:
            window_start = fm.target_time
            window_end = fm.target_time + timedelta(minutes=10)
            if window_start.tzinfo is None:
                window_start = window_start.replace(tzinfo=timezone.utc)
            if window_end.tzinfo is None:
                window_end = window_end.replace(tzinfo=timezone.utc)

            actual_res = await self.db.execute(
                select(func.count(Order.id)).where(
                    and_(
                        Order.store_id == fm.store_id,
                        Order.created_at >= window_start,
                        Order.created_at < window_end,
                    )
                )
            )
            actual_count = int(actual_res.scalar() or 0)
            actual_per_min = actual_count / 10.0

            epsilon = 1e-6
            ape = abs(actual_per_min - fm.predicted_orders_per_min) / max(actual_per_min, epsilon)
            ape_list.append(ape)

        mape = (sum(ape_list) / len(ape_list)) * 100 if ape_list else 0.0
        accuracy = max(0.0, 1.0 - mape / 100)

        return _build_response(
            "forecast_mape",
            accuracy,
            {"mape_pct": round(mape, 2), "windows_evaluated": len(ape_list)},
        )

    async def rider_utilisation(self) -> Dict[str, Any]:
        """
        active_time / shift_time per rider, aggregated.
        Uses shift_active_seconds (accumulated by sweep) / shift duration.
        """
        now = datetime.now(timezone.utc)

        riders_res = await self.db.execute(
            select(Rider).where(
                and_(
                    Rider.shift_end_time > now,
                    Rider.shift_start_time.isnot(None),
                )
            )
        )
        riders = riders_res.scalars().all()

        if not riders:
            return _build_response("rider_utilisation", None, {"note": "No active riders with shift data"})

        utilisation_scores = []
        for rider in riders:
            shift_start = rider.shift_start_time
            if shift_start is None:
                continue
            if shift_start.tzinfo is None:
                shift_start = shift_start.replace(tzinfo=timezone.utc)
            shift_end = rider.shift_end_time
            if shift_end.tzinfo is None:
                shift_end = shift_end.replace(tzinfo=timezone.utc)

            shift_total_sec = (min(now, shift_end) - shift_start).total_seconds()
            if shift_total_sec <= 0:
                continue
            score = min(1.0, rider.shift_active_seconds / shift_total_sec)
            utilisation_scores.append(score)

        if not utilisation_scores:
            return _build_response("rider_utilisation", None, {"note": "No riders with valid shift durations"})

        avg_utilisation = sum(utilisation_scores) / len(utilisation_scores)
        return _build_response(
            "rider_utilisation",
            avg_utilisation,
            {"rider_count": len(utilisation_scores)},
        )
