# app/modules/communities/service.py
from __future__ import annotations

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException
from app.models.community import Community
from app.modules.communities.repository import CommunityRepository
from app.modules.communities.schemas import CommunityCreate, CommunityUpdate


class CommunityService:
    def __init__(self, db: AsyncSession):
        self.repo = CommunityRepository(db)

    async def create_community(self, data: CommunityCreate) -> Community:
        community = Community(
            id=data.id,
            name=data.name,
            centroid_latitude=data.centroid_latitude,
            centroid_longitude=data.centroid_longitude,
            polygon=data.polygon,
            entry_points=data.entry_points,
            avg_walk_time_min=data.avg_walk_time_min,
            batch_window_sec=data.batch_window_sec,
            max_batch_size=data.max_batch_size
        )
        res = await self.repo.create_community(community)
        await self.repo.db.commit()
        return res

    async def get_all_communities(self) -> List[Community]:
        return await self.repo.get_all()

    async def get_community(self, community_id: str) -> Community:
        community = await self.repo.get_by_id(community_id)
        if not community:
            raise ResourceNotFoundException("Community geofence not found")
        return community

    async def update_community(self, community_id: str, data: CommunityUpdate) -> Community:
        community = await self.get_community(community_id)
        updated = await self.repo.update(community, data)
        await self.repo.db.commit()
        return updated

    async def delete_community(self, community_id: str):
        community = await self.get_community(community_id)
        await self.repo.delete(community)
        await self.repo.db.commit()