# app/modules/stores/service.py
from __future__ import annotations

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.stores.repository import StoreRepository
from app.modules.stores.schemas import StoreCreate, StoreUpdate
from app.models.store import Store
from app.core.exceptions import ResourceNotFoundException, IMSException

def validate_coordinates(latitude: Optional[float], longitude: Optional[float]):
    """Validates geographic boundaries and ensures coordinate pair completeness [1]."""
    if latitude is not None:
        if not (-90.0 <= latitude <= 90.0):
            raise IMSException("Latitude must be between -90 and 90 degrees", 400)
    if longitude is not None:
        if not (-180.0 <= longitude <= 180.0):
            raise IMSException("Longitude must be between -180 and 180 degrees", 400)
    # Ensure latitude and longitude are supplied as a pair
    if (latitude is None) != (longitude is None):
        raise IMSException("Both latitude and longitude must be provided together", 400)


class StoreService:
    def __init__(self, db: AsyncSession):
        self.repo = StoreRepository(db)

    async def create_store(self, store_data: StoreCreate) -> Store:
        existing = await self.repo.get_store_by_name(store_data.name)
        if existing:
            raise IMSException(f"Store with name '{store_data.name}' already exists", 400)
        
        # Enforce range limits
        validate_coordinates(store_data.latitude, store_data.longitude)
        
        db_store = await self.repo.create_store(store_data)
        await self.repo.db.commit()
        return db_store

    async def get_store_by_id(self, store_id: int) -> Store:
        store = await self.repo.get_store_by_id(store_id)
        if not store:
            raise ResourceNotFoundException(f"Store with ID {store_id} not found")
        return store

    async def get_all_stores(self, skip: int = 0, limit: int = 100) -> List[Store]:
        return await self.repo.get_all_stores(skip, limit)

    async def update_store(self, store_id: int, update_data: StoreUpdate) -> Store:
        store = await self.get_store_by_id(store_id)
        if update_data.name:
            existing = await self.repo.get_store_by_name(update_data.name)
            if existing and existing.id != store_id:
                raise IMSException(f"Store with name '{update_data.name}' already exists", 400)
        
        # Merge old and new coordinate values to validate the complete pair state
        new_lat = update_data.latitude if update_data.latitude is not None else store.latitude
        new_lon = update_data.longitude if update_data.longitude is not None else store.longitude
        validate_coordinates(new_lat, new_lon)
        
        db_store = await self.repo.update_store(store, update_data)
        await self.repo.db.commit()
        return db_store