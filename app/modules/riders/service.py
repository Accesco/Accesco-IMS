# app/modules/riders/service.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rider import Rider
from app.modules.riders.repository import RiderRepository
from app.modules.riders.schemas import RiderCreate, RiderUpdate


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
    async def update_rider(self, rider_id: int, rider_data: RiderUpdate) -> Rider:
        # 1. Fetch the existing rider (this automatically handles the 404 Not Found logic)
        rider = await self.get_rider(rider_id)

        # 2. Extract only the fields that were provided in the request body
        update_data = rider_data.model_dump(exclude_unset=True)

        # 3. Apply the updates to the SQLAlchemy model instance
        for key, value in update_data.items():
            setattr(rider, key, value)

        # 4. Commit the transaction and refresh the instance
        await self.repo.db.commit()
        await self.repo.db.refresh(rider)
        
        return rider
    
    async def delete_rider(self, rider_id: int) -> None:
        # 1. Fetch the existing rider (this automatically verifies they exist and handles the 404)
        rider = await self.get_rider(rider_id)

        # 2. Delete the rider instance from the session
        await self.repo.db.delete(rider)

        # 3. Commit the transaction to the database
        await self.repo.db.commit()