from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.modules.auth.routes import RoleChecker
from app.modules.replenishment.schemas import (
    ReplenishmentCheckRequest,
    ReplenishmentCheckResponse,
    ReplenishmentRecommendationResponse,
    ReplenishmentConvertResponse,
)
from app.modules.replenishment.service import ReplenishmentService

router = APIRouter(prefix="/replenishment", tags=["replenishment"])

# Role permission: Admin and ProcurementManager can access replenishment features
admin_or_procurement = RoleChecker(["Admin", "ProcurementManager"])


@router.post(
    "/check/{store_id}",
    response_model=ReplenishmentCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger replenishment check for a store",
    description="Sends inventory data to the ML Replenishment Engine and returns recommendations for SKUs that need reordering.",
)
async def check_store_replenishment(
    store_id: int,
    request_body: Optional[ReplenishmentCheckRequest] = None,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_procurement),
):
    service = ReplenishmentService(db)
    product_ids = request_body.product_ids if request_body else None
    recommendations = await service.check_store_replenishment(store_id, product_ids)
    return ReplenishmentCheckResponse(
        store_id=store_id,
        recommendations_generated=len(recommendations),
        recommendations=recommendations,
    )


@router.get(
    "/recommendations",
    response_model=List[ReplenishmentRecommendationResponse],
    summary="List replenishment recommendations",
    description="Retrieve all replenishment recommendations, optionally filtered by store and status.",
)
async def get_recommendations(
    store_id: Optional[int] = None,
    rec_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_procurement),
):
    service = ReplenishmentService(db)
    return await service.get_recommendations(store_id, rec_status, skip, limit)


@router.get(
    "/recommendations/{rec_id}",
    response_model=ReplenishmentRecommendationResponse,
    summary="Get a single recommendation",
    description="Retrieve a specific replenishment recommendation by ID.",
)
async def get_recommendation(
    rec_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(admin_or_procurement),
):
    service = ReplenishmentService(db)
    return await service.get_recommendation_by_id(rec_id)


@router.post(
    "/recommendations/{rec_id}/approve",
    response_model=ReplenishmentRecommendationResponse,
    summary="Approve a recommendation",
    description="Approve a PENDING recommendation. Status changes from PENDING to APPROVED.",
)
async def approve_recommendation(
    rec_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(admin_or_procurement),
):
    service = ReplenishmentService(db)
    return await service.approve_recommendation(rec_id, user_id=current_user.id)


@router.post(
    "/recommendations/{rec_id}/reject",
    response_model=ReplenishmentRecommendationResponse,
    summary="Reject a recommendation",
    description="Reject a PENDING recommendation. Status changes from PENDING to REJECTED.",
)
async def reject_recommendation(
    rec_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(admin_or_procurement),
):
    service = ReplenishmentService(db)
    return await service.reject_recommendation(rec_id, user_id=current_user.id)


@router.post(
    "/recommendations/{rec_id}/convert",
    response_model=ReplenishmentConvertResponse,
    summary="Convert recommendation to Purchase Order",
    description="Convert an APPROVED recommendation into a Purchase Order. Status changes from APPROVED to CONVERTED.",
)
async def convert_to_purchase_order(
    rec_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(admin_or_procurement),
):
    service = ReplenishmentService(db)
    rec = await service.convert_to_purchase_order(rec_id, user_id=current_user.id)
    return ReplenishmentConvertResponse(
        recommendation=rec,
        purchase_order_id=rec.purchase_order_id,
    )
