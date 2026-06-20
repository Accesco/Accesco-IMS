from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.procurement import PurchaseOrder, PurchaseOrderItem
from app.modules.procurement.schemas import PurchaseOrderCreate

class ProcurementRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_purchase_order_by_id(self, po_id: int) -> Optional[PurchaseOrder]:
        result = await self.db.execute(
            select(PurchaseOrder).where(PurchaseOrder.id == po_id)
        )
        return result.scalar_one_or_none()

    async def get_all_purchase_orders(self, skip: int = 0, limit: int = 100) -> List[PurchaseOrder]:
        result = await self.db.execute(
            select(PurchaseOrder).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def create_purchase_order(self, po_data: PurchaseOrderCreate) -> PurchaseOrder:
        db_po = PurchaseOrder(
            supplier_name=po_data.supplier_name,
            status=po_data.status
        )
        self.db.add(db_po)
        await self.db.flush()  # get PO ID

        for item in po_data.items:
            db_item = PurchaseOrderItem(
                purchase_order_id=db_po.id,
                product_id=item.product_id,
                quantity=item.quantity
            )
            self.db.add(db_item)
            
        await self.db.flush()
        await self.db.refresh(db_po, attribute_names=["items"])  # Eagerly load items; avoids async lazy-load MissingGreenlet
        return db_po

    async def update_purchase_order_status(self, po: PurchaseOrder, status: str) -> PurchaseOrder:
        po.status = status
        await self.db.flush()
        return po
