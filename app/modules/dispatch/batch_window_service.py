
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.models.order import Order
from app.core.forecasting import predict_holt_winters, calculate_optimal_batch_window

class BatchWindowOptimizer:
    def __init__(self, db: AsyncSession, redis_client):
        self.db = db
        self.redis = redis_client

    async def determine_optimal_window_for_community(self, community_id: str) -> int:
        cache_key = f"community:window:{community_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return int(cached)

        now = datetime.now(timezone.utc)
        intervals = []
        for i in range(6):
            start = now - timedelta(minutes=(i+1)*10)
            end = now - timedelta(minutes=i*10)
            
            res = await self.db.execute(
                select(func.count(Order.id)).where(
                    and_(
                        Order.community_id == community_id,
                        Order.created_at >= start,
                        Order.created_at < end
                    )
                )
            )
            intervals.append(float(res.scalar() or 0))
            
        intervals.reverse()

        predicted_arrival_rate_10min = predict_holt_winters(intervals, alpha=0.4, beta=0.3)
        predicted_orders_per_min = predicted_arrival_rate_10min / 10.0

        optimal_window_sec, _ = calculate_optimal_batch_window(predicted_orders_per_min)

        await self.redis.set(cache_key, optimal_window_sec, ex=600)
        return optimal_window_sec