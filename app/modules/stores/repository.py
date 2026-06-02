from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.store import Store
from app.modules.stores.schemas import StoreCreate, StoreUpdate

class StoreRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_store_by_id(self, store_id: int) -> Optional[Store]:
        result = await self.db.execute(select(Store).where(Store.id == store_id))
        return result.scalar_one_or_none()

    async def get_store_by_name(self, name: str) -> Optional[Store]:
        result = await self.db.execute(select(Store).where(Store.name == name))
        return result.scalar_one_or_none()

    async def get_all_stores(self, skip: int = 0, limit: int = 100) -> List[Store]:
        result = await self.db.execute(select(Store).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create_store(self, store_data: StoreCreate) -> Store:
        db_store = Store(
            name=store_data.name,
            address=store_data.address,
            city=store_data.city,
            state=store_data.state,
            active=store_data.active
        )
        self.db.add(db_store)
        await self.db.flush()
        return db_store

    async def update_store(self, store: Store, update_data: StoreUpdate) -> Store:
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(store, field, value)
        await self.db.flush()
        return store
