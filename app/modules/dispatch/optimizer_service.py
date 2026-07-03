
from __future__ import annotations

import logging
import numpy as np
from datetime import datetime, timezone
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Tuple, Dict, Any

from app.models.rider import Rider
from app.models.order import Order
from app.models.batch import Batch
from app.models.store import Store
from app.core.geo_utils import calculate_assignment_cost, solve_hungarian_exact, solve_auction_approximate
from app.modules.dispatch import repository

logger = logging.getLogger("dispatch_optimizer")


class GlobalDispatchOptimizer:
    def __init__(self, db: AsyncSession, redis_client):
        self.db = db
        self.redis = redis_client

    async def execute_global_optimization_sweep(self) -> int:
        # 1. Acquire global execution distributed lock (Redlock pattern)
        lock_acquired = await self.redis.set("lock:dispatch_optimizer", "locked", ex=10, nx=True)
        if not lock_acquired:
            logger.info("Global optimizer sweep already executing on another node. Skipping.")
            return 0

        try:
            # 2. Extract Eligible Pool with row-level locks [1, 11.1]
            unassigned_orders = await self._get_unassigned_orders()
            active_draft_batches = await self._get_draft_batches()
            unassigned_work_items: List[Order | Batch] = list(unassigned_orders) + list(active_draft_batches)
            
            eligible_riders = await repository.get_eligible_riders_for_assignment(self.db)

            if not unassigned_work_items or not eligible_riders:
                return 0

            # 3. Construct Assignment Cost Matrix (Section 08) [11.1]
            cost_matrix, rider_index_map, item_index_map = await self._build_cost_matrix(
                eligible_riders, unassigned_work_items
            )

            # 4. Run Matrix Complexity Scale Solver [11.1]
            n_riders = len(eligible_riders)
            n_items = len(unassigned_work_items)
            
            if max(n_riders, n_items) <= 100:
                logger.info(f"Solving exact {n_riders}x{n_items} assignment via Hungarian Algorithm.")
                matches = solve_hungarian_exact(cost_matrix)
            else:
                logger.info(f"Solving approximate {n_riders}x{n_items} assignment via Auction Algorithm.")
                matches = solve_auction_approximate(cost_matrix)

            # 5. Commit Matched Assignments Transactionally with error rollbacks [1]
            matched_count = 0
            for r_idx, i_idx in matches:
                # Boundary Check: If the indices match dummy padded columns, skip them [11.1]
                if r_idx >= n_riders or i_idx >= n_items:
                    continue

                # Soft exclusion check
                if cost_matrix[r_idx, i_idx] >= 9.9:
                    continue

                rider = rider_index_map[r_idx]
                work_item = item_index_map[i_idx]

                await self._apply_assignment(rider, work_item)
                matched_count += 1

            if matched_count > 0:
                await self.db.commit()

            return matched_count

        except Exception as error:
            await self.db.rollback()
            logger.error(f"Failed to commit global optimizer assignments: {str(error)}")
            raise error

        finally:
            await self.redis.delete("lock:dispatch_optimizer")

    async def _get_unassigned_orders(self) -> List[Order]:
        res = await self.db.execute(
            select(Order)
            .where(and_(Order.assignment_status == "UNASSIGNED", Order.batch_id == None))
            .with_for_update()
        )
        return list(res.scalars().all())

    async def _get_draft_batches(self) -> List[Batch]:
        res = await self.db.execute(
            select(Batch)
            .options(selectinload(Batch.orders))
            .where(Batch.status == "DRAFT")
            .with_for_update()
        )
        return list(res.scalars().all())

    async def _build_cost_matrix(
        self, 
        riders: List[Rider], 
        items: List[Order | Batch]
    ) -> Tuple[np.ndarray, Dict[int, Rider], Dict[int, Order | Batch]]:
        n, m = len(riders), len(items)
        cost_matrix = np.zeros((n, m))
        
        rider_map = {idx: r for idx, r in enumerate(riders)}
        item_map = {idx: i for idx, i in enumerate(items)}

        now = datetime.now(timezone.utc)

        for i, rider in enumerate(riders):
            for j, item in enumerate(items):
                is_batch = isinstance(item, Batch)
                proxy_order = item.orders[0] if is_batch else item
                store = await repository.get_store_by_id(self.db, proxy_order.store_id)
                
                if not store:
                    cost_matrix[i, j] = 9.9
                    continue

                load = await repository.get_rider_active_load_count(self.db, rider.id)
                sla_time_left = (proxy_order.sla_deadline.replace(tzinfo=timezone.utc) - now).total_seconds()

                cost = calculate_assignment_cost(
                    rider=rider,
                    store=store,
                    target_latitude=proxy_order.latitude,
                    target_longitude=proxy_order.longitude,
                    active_load_count=load,
                    is_batch=is_batch,
                    sla_time_left_sec=sla_time_left
                )
                cost_matrix[i, j] = cost

        # Pad matrix to make it square if N != M
        if n != m:
            size = max(n, m)
            padded = np.full((size, size), 9.9)
            padded[:n, :m] = cost_matrix
            cost_matrix = padded

        return cost_matrix, rider_map, item_map

    async def _apply_assignment(self, rider: Rider, item: Order | Batch):
        now = datetime.now(timezone.utc)
        
        if isinstance(item, Batch):
            item.offered_rider_id = rider.id
            item.assignment_offered_at = now
            item.status = "OFFERED"
            for o in item.orders:
                o.assignment_status = "OFFERED"
                o.offered_rider_id = rider.id
                o.assignment_offered_at = now
        else:
            item.offered_rider_id = rider.id
            item.assignment_offered_at = now
            item.assignment_status = "OFFERED"

        rider.is_available = False
        rider.status = "ASSIGNED"