from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, true
from sqlalchemy.exc import IntegrityError
from app.core.exceptions import IMSException

from app.models.rider import Rider


class RiderRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_rider(self, rider: Rider):
        try:
            self.db.add(rider)
            await self.db.flush()
            return rider
        except IntegrityError:
            await self.db.rollback()
            raise IMSException("Rider with this phone number already exists", 400)

    async def get_rider_by_id(self, rider_id: int):
        result = await self.db.execute(
            select(Rider).where(Rider.id == rider_id)
        )
        return result.scalar_one_or_none()

    async def get_all_riders(self):
        result = await self.db.execute(
            select(Rider)
        )
        return result.scalars().all()

    async def get_available_riders(self):
        result = await self.db.execute(
            select(Rider).where(
                 Rider.is_available == true()
            )
        )
        return result.scalars().all()