from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.stores.repository import StoreRepository
from app.modules.stores.schemas import StoreCreate, StoreUpdate
from app.models.store import Store
from app.core.exceptions import ResourceNotFoundException, IMSException

class StoreService:
    def __init__(self, db: AsyncSession):
        self.repo = StoreRepository(db)

    async def create_store(self, store_data: StoreCreate) -> Store:
        existing = await self.repo.get_store_by_name(store_data.name)
        if existing:
            raise IMSException(f"Store with name '{store_data.name}' already exists", 400)
        return await self.repo.create_store(store_data)

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
        return await self.repo.update_store(store, update_data)
