# app/modules/riders/service.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rider import Rider
from app.modules.riders.repository import RiderRepository
from app.modules.riders.schemas import RiderCreate


class ResourceNotFoundException(Exception):
    pass


class RiderService:
    def __init__(self, db: AsyncSession):
        self.repo = RiderRepository(db)

    async def create_rider(self, rider_data: RiderCreate) -> Rider:
        # Default shift end time to 12 hours from now to pass eligibility (Section 03)
        default_shift_end = datetime.now(timezone.utc) + timedelta(hours=12)
        initial_heartbeat = datetime.now(timezone.utc)

        rider = Rider(
            name=rider_data.name,
            phone=rider_data.phone,
            latitude=rider_data.latitude,
            longitude=rider_data.longitude,
            is_available=rider_data.is_available,
            status=rider_data.status,
            shift_end_time=default_shift_end,
            last_heartbeat_at=initial_heartbeat,
            battery_level=100.0,
            performance_score=1.0
        )

        res = await self.repo.create_rider(rider)
        await self.repo.db.commit()
        return res

    async def get_all_riders(self) -> List[Rider]:
        return await self.repo.get_all_riders()

    async def get_rider(self, rider_id: int) -> Rider:
        rider = await self.repo.get_rider_by_id(rider_id)
        if not rider:
            raise ResourceNotFoundException("Rider not found")
        return rider