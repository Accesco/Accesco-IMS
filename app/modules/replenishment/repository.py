from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.replenishment import ReplenishmentRecommendation


class ReplenishmentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_recommendation(
        self,
        store_id: int,
        product_id: int,
        sku_id: str,
        recommended_quantity: int,
        confidence_score: float,
        ml_response_payload: Optional[dict] = None,
    ) -> ReplenishmentRecommendation:
        rec = ReplenishmentRecommendation(
            store_id=store_id,
            product_id=product_id,
            sku_id=sku_id,
            recommended_quantity=recommended_quantity,
            confidence_score=confidence_score,
            status="PENDING",
            ml_response_payload=ml_response_payload,
        )
        self.db.add(rec)
        await self.db.flush()
        await self.db.refresh(rec)
        return rec

    async def get_recommendation_by_id(self, rec_id: int) -> Optional[ReplenishmentRecommendation]:
        result = await self.db.execute(
            select(ReplenishmentRecommendation).where(ReplenishmentRecommendation.id == rec_id)
        )
        return result.scalar_one_or_none()

    async def get_recommendations(
        self,
        store_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ReplenishmentRecommendation]:
        query = select(ReplenishmentRecommendation)
        if store_id is not None:
            query = query.where(ReplenishmentRecommendation.store_id == store_id)
        if status is not None:
            query = query.where(ReplenishmentRecommendation.status == status)
        query = query.order_by(ReplenishmentRecommendation.created_at.desc())
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_recommendation_status(
        self, rec: ReplenishmentRecommendation, status: str
    ) -> ReplenishmentRecommendation:
        rec.status = status
        await self.db.flush()
        return rec

    async def link_purchase_order(
        self, rec: ReplenishmentRecommendation, po_id: int
    ) -> ReplenishmentRecommendation:
        rec.purchase_order_id = po_id
        rec.status = "CONVERTED"
        await self.db.flush()
        return rec
