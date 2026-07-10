"""
Business logic for the Replenishment module.

Orchestrates the flow:
    Inventory Data → ML Engine → Recommendations → Approve → Purchase Order
"""
import logging
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException, IMSException
from app.core.events import create_outbox_event
from app.models.replenishment import ReplenishmentRecommendation
from app.modules.replenishment.repository import ReplenishmentRepository
from app.modules.replenishment.ml_client import build_ml_payload, call_ml_engine, DEFAULT_REORDER_QUANTITY
from app.modules.inventory.repository import InventoryRepository
from app.modules.procurement.service import ProcurementService
from app.modules.procurement.schemas import PurchaseOrderCreate, PurchaseOrderItemCreate
from app.modules.audit.service import AuditLogService

logger = logging.getLogger(__name__)


class ReplenishmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ReplenishmentRepository(db)
        self.inv_repo = InventoryRepository(db)

    async def check_store_replenishment(
        self,
        store_id: int,
        product_ids: Optional[List[int]] = None,
    ) -> List[ReplenishmentRecommendation]:
        """
        Trigger a replenishment check for all (or filtered) inventory items in a store.

        1. Fetch inventory items for the store
        2. Transform each into ML payload format
        3. Call the ML engine for each SKU
        4. Persist recommendations for items predicted as needing reorder
        5. Return the list of new recommendations
        """
        # Get all inventory items for this store
        items = await self.inv_repo.get_items_by_store(store_id)
        if not items:
            raise ResourceNotFoundException(f"No inventory items found for store {store_id}")

        # Optionally filter to specific products
        if product_ids:
            items = [item for item in items if item.product_id in product_ids]
            if not items:
                raise ResourceNotFoundException(
                    f"No inventory items found for the specified products in store {store_id}"
                )

        recommendations = []

        for item in items:
            # Build the ML telemetry payload from IMS data
            payload = build_ml_payload(
                sku_id=item.product.sku,
                on_hand=item.available_quantity,
                reserved=item.reserved_quantity,
                store_name=item.store.name if item.store else None,
                temp_zone=item.product.category if item.product else None,
            )

            # Call the ML engine
            ml_response = await call_ml_engine(payload)

            # Check if ML engine flagged this SKU for reorder
            if ml_response.get("event_type") == "AUTOMATED_PO_TRIGGERED":
                confidence = ml_response.get("confidence_score", 0.0)

                # Calculate recommended quantity based on velocity or use default
                recommended_qty = DEFAULT_REORDER_QUANTITY

                rec = await self.repo.create_recommendation(
                    store_id=store_id,
                    product_id=item.product_id,
                    sku_id=item.product.sku,
                    recommended_quantity=recommended_qty,
                    confidence_score=confidence,
                    ml_response_payload=ml_response,
                )
                recommendations.append(rec)

                logger.info(
                    "Replenishment recommendation created: store=%d product=%d sku=%s confidence=%.4f",
                    store_id, item.product_id, item.product.sku, confidence,
                )

        # Emit outbox event for the batch check
        if recommendations:
            await create_outbox_event(
                self.db,
                "replenishment.checked",
                {
                    "store_id": store_id,
                    "recommendations_count": len(recommendations),
                    "product_ids": [r.product_id for r in recommendations],
                },
            )

        await self.db.commit()

        # Re-fetch to get fully hydrated objects after commit
        result = []
        for rec in recommendations:
            refreshed = await self.repo.get_recommendation_by_id(rec.id)
            if refreshed:
                result.append(refreshed)

        return result

    async def get_recommendations(
        self,
        store_id: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ReplenishmentRecommendation]:
        """Get filtered list of recommendations."""
        return await self.repo.get_recommendations(store_id, status, skip, limit)

    async def get_recommendation_by_id(self, rec_id: int) -> ReplenishmentRecommendation:
        """Get a single recommendation by ID or raise 404."""
        rec = await self.repo.get_recommendation_by_id(rec_id)
        if not rec:
            raise ResourceNotFoundException(f"Recommendation with ID {rec_id} not found")
        return rec

    async def approve_recommendation(self, rec_id: int, user_id: Optional[int] = None) -> ReplenishmentRecommendation:
        """
        Approve a PENDING recommendation.
        Status: PENDING → APPROVED
        """
        rec = await self.get_recommendation_by_id(rec_id)

        if rec.status != "PENDING":
            raise IMSException(
                f"Cannot approve recommendation {rec_id}: current status is {rec.status} (must be PENDING)", 400
            )

        old_status = rec.status
        await self.repo.update_recommendation_status(rec, "APPROVED")

        await AuditLogService(self.db).log_action(
            module="Replenishment",
            action="APPROVE_RECOMMENDATION",
            user_id=user_id,
            entity_id=str(rec_id),
            old_values={"status": old_status},
            new_values={"status": "APPROVED"},
        )

        await create_outbox_event(
            self.db,
            "replenishment.approved",
            {
                "recommendation_id": rec.id,
                "store_id": rec.store_id,
                "product_id": rec.product_id,
                "recommended_quantity": rec.recommended_quantity,
            },
        )

        await self.db.commit()
        return await self.get_recommendation_by_id(rec_id)

    async def reject_recommendation(self, rec_id: int, user_id: Optional[int] = None) -> ReplenishmentRecommendation:
        """
        Reject a PENDING recommendation.
        Status: PENDING → REJECTED
        """
        rec = await self.get_recommendation_by_id(rec_id)

        if rec.status != "PENDING":
            raise IMSException(
                f"Cannot reject recommendation {rec_id}: current status is {rec.status} (must be PENDING)", 400
            )

        old_status = rec.status
        await self.repo.update_recommendation_status(rec, "REJECTED")

        await AuditLogService(self.db).log_action(
            module="Replenishment",
            action="REJECT_RECOMMENDATION",
            user_id=user_id,
            entity_id=str(rec_id),
            old_values={"status": old_status},
            new_values={"status": "REJECTED"},
        )

        await self.db.commit()
        return await self.get_recommendation_by_id(rec_id)

    async def convert_to_purchase_order(self, rec_id: int, user_id: Optional[int] = None) -> ReplenishmentRecommendation:
        """
        Convert an APPROVED recommendation into a Purchase Order.
        Status: APPROVED → CONVERTED

        Creates a PO via the existing ProcurementService and links it back.
        """
        rec = await self.get_recommendation_by_id(rec_id)

        if rec.status != "APPROVED":
            raise IMSException(
                f"Cannot convert recommendation {rec_id}: current status is {rec.status} (must be APPROVED)", 400
            )

        # Create Purchase Order via existing procurement module
        procurement_service = ProcurementService(self.db)
        po_data = PurchaseOrderCreate(
            supplier_name="AutoSupplier-Replenishment",
            status="DRAFT",
            items=[
                PurchaseOrderItemCreate(
                    product_id=rec.product_id,
                    quantity=rec.recommended_quantity,
                )
            ],
        )
        po = await procurement_service.create_purchase_order(po_data)

        # Link PO to the recommendation and update status
        await self.repo.link_purchase_order(rec, po.id)

        await AuditLogService(self.db).log_action(
            module="Replenishment",
            action="CONVERT_TO_PO",
            user_id=user_id,
            entity_id=str(rec_id),
            old_values={"status": "APPROVED"},
            new_values={"status": "CONVERTED", "purchase_order_id": po.id},
        )

        await create_outbox_event(
            self.db,
            "replenishment.converted",
            {
                "recommendation_id": rec.id,
                "store_id": rec.store_id,
                "product_id": rec.product_id,
                "purchase_order_id": po.id,
                "quantity": rec.recommended_quantity,
            },
        )

        await self.db.commit()
        return await self.get_recommendation_by_id(rec_id)
