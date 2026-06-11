from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.routes import RoleChecker
from app.modules.riders.service import RiderService
from app.modules.riders.schemas import (
    RiderCreate,
    RiderResponse
)

router = APIRouter(
    prefix="/riders",
    tags=["riders"]
)

# Role permission helpers
admin_or_store_manager = RoleChecker(["Admin", "StoreManager"])
all_authorized = RoleChecker(["Admin", "StoreManager", "Viewer"])


@router.post("", response_model=RiderResponse)
async def create_rider(
    rider_data: RiderCreate,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_store_manager)
):
    """Create a new rider.

    Requires authentication. Allowed roles: Admin, StoreManager.
    Returns 401 if unauthenticated, 403 if the role is not permitted.
    """
    service = RiderService(db)
    return await service.create_rider(rider_data)


@router.get("", response_model=list[RiderResponse])
async def get_riders(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(all_authorized)
):
    """List all riders.

    Requires authentication. Allowed roles: Admin, StoreManager, Viewer.
    Returns 401 if unauthenticated, 403 if the role is not permitted.
    """
    service = RiderService(db)
    return await service.get_all_riders()
