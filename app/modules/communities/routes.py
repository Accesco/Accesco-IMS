# app/modules/communities/routes.py
from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.routes import RoleChecker
from app.modules.communities.service import CommunityService
from app.modules.communities.schemas import (
    CommunityCreate,
    CommunityUpdate,
    CommunityResponse
)

router = APIRouter(
    prefix="/communities",
    tags=["Communities"]
)

admin_or_store_manager = RoleChecker(["Admin", "StoreManager"])
all_authorized = RoleChecker(["Admin", "StoreManager", "Viewer"])


@router.post("", response_model=CommunityResponse)
async def create_community(
    data: CommunityCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager)
):
    service = CommunityService(db)
    return await service.create_community(data)


@router.get("", response_model=List[CommunityResponse])
async def get_all_communities(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized)
):
    service = CommunityService(db)
    return await service.get_all_communities()


@router.get("/{community_id}", response_model=CommunityResponse)
async def get_community(
    community_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized)
):
    service = CommunityService(db)
    return await service.get_community(community_id)


@router.put("/{community_id}", response_model=CommunityResponse)
async def update_community(
    community_id: str,
    data: CommunityUpdate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager)
):
    service = CommunityService(db)
    return await service.update_community(community_id, data)


@router.delete("/{community_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_community(
    community_id: str,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager)
):
    service = CommunityService(db)
    await service.delete_community(community_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)