from app.models.rider import Rider
from app.modules.riders.repository import RiderRepository
from app.modules.riders.schemas import RiderCreate


class RiderService:
    def __init__(self, db):
        self.repo = RiderRepository(db)

    async def create_rider(self, rider_data: RiderCreate):
        rider = Rider(
            name=rider_data.name,
            phone=rider_data.phone,
            latitude=rider_data.latitude,
            longitude=rider_data.longitude,
            is_available=rider_data.is_available,
            status=rider_data.status
        )

        return await self.repo.create_rider(rider)

    async def get_all_riders(self):
        return await self.repo.get_all_riders()

    async def get_rider(self, rider_id: int):
        return await self.repo.get_rider_by_id(rider_id)