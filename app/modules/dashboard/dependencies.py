from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis, RedisService
from app.modules.dashboard.repository import DashboardRepository
from app.modules.dashboard.provider import DashboardProvider
from app.modules.dashboard.service import DashboardService

async def get_dashboard_service(
    db: AsyncSession = Depends(get_db),
    redis: RedisService = Depends(get_redis)
) -> DashboardService:
    repository = DashboardRepository(db)
    provider = DashboardProvider(repository)
    return DashboardService(provider, redis)
