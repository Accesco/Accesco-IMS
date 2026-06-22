# app/modules/communities/repository.py
from __future__ import annotations

from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import IMSException
from app.models.community import Community
from app.modules.communities.schemas import CommunityUpdate


class CommunityRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_community(self, community: Community) -> Community:
        try:
            self.db.add(community)
            await self.db.flush()
            return community
        except IntegrityError:
            await self.db.rollback()
            raise IMSException("Community ID already exists", 400)

    async def get_by_id(self, community_id: str) -> Optional[Community]:
        result = await self.db.execute(
            select(Community).where(Community.id == community_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> List[Community]:
        result = await self.db.execute(select(Community))
        return list(result.scalars().all())

    async def update(self, community: Community, update_data: CommunityUpdate) -> Community:
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(community, field, value)
        await self.db.flush()
        return community

    async def delete(self, community: Community):
        await self.db.delete(community)
        await self.db.flush()