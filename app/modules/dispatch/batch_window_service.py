
from __future__ import annotations

import json
import math
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.order import Order
from app.core.forecasting import predict_holt_winters, calculate_optimal_batch_window
from app.modules.dispatch import repository


class BatchWindowOptimizer:
    def __init__(self, db: AsyncSession, redis_client):
        self.db = db
        self.redis = redis_client

    async def determine_optimal_window_for_community(self, community_id: str) -> int:
        """
        Computes the optimal batch window for a community using Holt-Winters exponential
        smoothing, caches the result in Redis, and persists ForecastMetric +
        CommunityDynamicWindow rows for historical accuracy analysis.
        """
        cache_key = f"community:window:{community_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return int(cached)

        now = datetime.now(timezone.utc)
        intervals = []
        for i in range(6):
            start = now - timedelta(minutes=(i + 1) * 10)
            end = now - timedelta(minutes=i * 10)

            from sqlalchemy import func as sqlfunc
            res = await self.db.execute(
                select(sqlfunc.count(Order.id)).where(
                    and_(
                        Order.community_id == community_id,
                        Order.created_at >= start,
                        Order.created_at < end,
                    )
                )
            )
            intervals.append(float(res.scalar() or 0))

        intervals.reverse()

        predicted_arrival_rate_10min = predict_holt_winters(intervals, alpha=0.4, beta=0.3)
        predicted_orders_per_min = predicted_arrival_rate_10min / 10.0

        optimal_window_sec, predicted_batch_size = calculate_optimal_batch_window(predicted_orders_per_min)

        # Cache in Redis (600 s TTL)
        await self.redis.set(cache_key, optimal_window_sec, ex=600)

        #  Persist forecast rows
     # store_id = 0  # No orders found for this community yet; store lookup unavailable
        store_id = await repository.get_store_id_for_community(self.db, community_id)
        if store_id is None:
            store_id = 0  # sentinel — no orders in community yet;  resolve via community→store mapping

        # Rider demand: simple heuristic — 1 rider per 3 predicted orders per min window
        predicted_rider_demand = max(1, math.ceil(predicted_orders_per_min * (optimal_window_sec / 60.0)))

        await repository.create_forecast_metric(
            db=self.db,
            store_id=store_id,
            target_time=now,
            predicted_orders_per_min=predicted_orders_per_min,
            predicted_rider_demand=predicted_rider_demand,
            predicted_batch_size=predicted_batch_size,
            recommended_batch_window_sec=optimal_window_sec,
        )

        await repository.create_community_dynamic_window(
            db=self.db,
            community_id=community_id,
            hour_of_day=now.hour,
            day_of_week=now.weekday(),
            order_velocity_weight=round(predicted_orders_per_min, 4),
            calculated_window_sec=optimal_window_sec,
        )
        # ─────────────────────────────────────────────────────────────────────

        return optimal_window_sec