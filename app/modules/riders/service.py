# app/modules/riders/service.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rider import Rider
from app.modules.riders.repository import RiderRepository
from app.modules.riders.schemas import RiderCreate, RiderUpdate
from app.modules.audit.service import AuditLogService


class ResourceNotFoundException(Exception):
    pass


class RiderService:
    def __init__(self, db: AsyncSession):
        self.repo = RiderRepository(db)

    async def create_rider(self, rider_data: RiderCreate, user_id: int = None) -> Rider:
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
        await self.repo.db.flush()

        await AuditLogService(self.repo.db).log_action(
            module="Riders",
            action="CREATE_RIDER",
            user_id=user_id,
            entity_id=str(res.id),
            new_values={"name": res.name, "phone": res.phone}
        )

        await self.repo.db.commit()
        return res

    async def get_all_riders(self) -> List[Rider]:
        return await self.repo.get_all_riders()

    async def get_rider(self, rider_id: int) -> Rider:
        rider = await self.repo.get_rider_by_id(rider_id)
        if not rider:
            raise ResourceNotFoundException("Rider not found")
        return rider

    async def update_rider(self, rider_id: int, rider_data: RiderUpdate, user_id: int = None) -> Rider:
        rider = await self.get_rider(rider_id)
        old_values = {
            k: getattr(rider, k) for k in rider_data.model_dump(exclude_unset=True).keys()
        }
        
        updated_rider = await self.repo.update_rider(rider, rider_data)
        
        new_values = rider_data.model_dump(exclude_unset=True)

        await AuditLogService(self.repo.db).log_action(
            module="Riders",
            action="UPDATE_RIDER",
            user_id=user_id,
            entity_id=str(updated_rider.id),
            old_values=old_values,
            new_values=new_values
        )

        await self.repo.db.commit()
        return updated_rider

    async def delete_rider(self, rider_id: int, user_id: int = None):
        rider = await self.get_rider(rider_id)
        
        await AuditLogService(self.repo.db).log_action(
            module="Riders",
            action="DELETE_RIDER",
            user_id=user_id,
            entity_id=str(rider.id),
            old_values={"name": rider.name, "phone": rider.phone}
        )
        
        await self.repo.delete_rider(rider)
        await self.repo.db.commit()