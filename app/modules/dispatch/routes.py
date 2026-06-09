from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.modules.dispatch.schemas import DispatchResponse
from app.modules.dispatch import service

router = APIRouter(
    tags=["Dispatch"]
)


@router.post(
    "/assign/{order_id}",
    response_model=DispatchResponse
)
async def assign_order(
    order_id: int,
    db=Depends(get_db)
):
    return await service.assign_order(db,order_id)