# app/modules/riders/repository.py
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IMSException
from app.models.rider import Rider
from app.modules.riders.schemas import RiderUpdate


class RiderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_rider(self, rider: Rider) -> Rider:
        try:
            self.db.add(rider)
            await self.db.flush()
            return rider
        except IntegrityError:
            await self.db.rollback()
            raise IMSException("Rider with this phone number already exists", 400)

    async def get_rider_by_id(self, rider_id: int) -> Optional[Rider]:
        result = await self.db.execute(
            select(Rider).where(Rider.id == rider_id)
        )
        return result.scalar_one_or_none()

    async def get_all_riders(self) -> List[Rider]:
        result = await self.db.execute(select(Rider))
        return list(result.scalars().all())

    async def get_available_riders(self) -> List[Rider]:
        result = await self.db.execute(
            select(Rider).where(Rider.is_available == true())
        )
        return list(result.scalars().all())

    async def update_rider(self, rider: Rider, update_data: RiderUpdate) -> Rider:
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(rider, field, value)
        await self.db.flush()
        return rider

    async def delete_rider(self, rider: Rider):
        await self.db.delete(rider)
        await self.db.flush()