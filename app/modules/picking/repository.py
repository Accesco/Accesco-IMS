from typing import List, Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.picking import PickWave, PickTask, PickTaskItem
from app.models.order import Order

class PickingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_wave(self, store_id: int) -> PickWave:
        wave = PickWave(store_id=store_id, status="PENDING")
        self.db.add(wave)
        await self.db.flush()
        return wave

    async def create_tasks_bulk(self, tasks: List[PickTask]) -> List[PickTask]:
        self.db.add_all(tasks)
        await self.db.flush()
        return tasks

    async def create_task_items_bulk(self, items: List[PickTaskItem]) -> List[PickTaskItem]:
        self.db.add_all(items)
        await self.db.flush()
        return items

    async def get_wave_by_id(self, wave_id: int) -> Optional[PickWave]:
        result = await self.db.execute(
            select(PickWave)
            .options(selectinload(PickWave.tasks).selectinload(PickTask.items))
            .where(PickWave.id == wave_id)
        )
        return result.scalar_one_or_none()

    async def get_waves(self, store_id: Optional[int] = None) -> List[PickWave]:
        query = select(PickWave)
        if store_id:
            query = query.where(PickWave.store_id == store_id)
        query = query.order_by(PickWave.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_task_by_id(self, task_id: int, lock: bool = False) -> Optional[PickTask]:
        query = select(PickTask).options(selectinload(PickTask.items)).where(PickTask.id == task_id)
        if lock:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_task_item_by_id(self, item_id: int, lock: bool = False) -> Optional[PickTaskItem]:
        query = select(PickTaskItem).where(PickTaskItem.id == item_id)
        if lock:
            query = query.with_for_update()
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_tasks(self, wave_id: Optional[int] = None, assignee_id: Optional[int] = None, status: Optional[str] = None) -> List[PickTask]:
        query = select(PickTask).options(selectinload(PickTask.items))
        if wave_id:
            query = query.where(PickTask.wave_id == wave_id)
        if assignee_id:
            query = query.where(PickTask.assigned_to == assignee_id)
        if status:
            query = query.where(PickTask.status == status)
        query = query.order_by(PickTask.created_at.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_uncompleted_tasks_count(self, wave_id: int) -> int:
        result = await self.db.execute(
            select(func.count(PickTask.id)).where(
                PickTask.wave_id == wave_id,
                PickTask.status != "COMPLETED"
            )
        )
        return result.scalar() or 0
