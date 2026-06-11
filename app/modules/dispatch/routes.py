from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.modules.auth.routes import RoleChecker
from app.modules.dispatch.schemas import DispatchResponse
from app.modules.dispatch import service

router = APIRouter(
    tags=["Dispatch"]
)

# Role permission helpers
admin_or_store_manager = RoleChecker(["Admin", "StoreManager"])


@router.post(
    "/assign/{order_id}",
    response_model=DispatchResponse
)
async def assign_order(
    order_id: int,
    db=Depends(get_db),
    _current_user=Depends(admin_or_store_manager)
):
    """Assign an available rider to an order.

    Requires authentication. Allowed roles: Admin, StoreManager.
    Returns 401 if unauthenticated, 403 if the role is not permitted.
    """
    return await service.assign_order(db, order_id)
