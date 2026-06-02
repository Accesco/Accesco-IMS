from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException, IMSException
from app.core.events import create_outbox_event
from app.models.procurement import PurchaseOrder
from app.modules.procurement.repository import ProcurementRepository
from app.modules.procurement.schemas import PurchaseOrderCreate, PurchaseOrderItemCreate
from app.modules.inventory.service import InventoryService

class ProcurementService:
    def __init__(self, db: AsyncSession):
        self.repo = ProcurementRepository(db)

    async def get_purchase_order_by_id(self, po_id: int) -> PurchaseOrder:
        po = await self.repo.get_purchase_order_by_id(po_id)
        if not po:
            raise ResourceNotFoundException(f"Purchase Order with ID {po_id} not found")
        return po

    async def get_all_purchase_orders(self, skip: int = 0, limit: int = 100) -> List[PurchaseOrder]:
        return await self.repo.get_all_purchase_orders(skip, limit)

    async def create_purchase_order(self, po_data: PurchaseOrderCreate) -> PurchaseOrder:
        if not po_data.items:
            raise IMSException("Cannot create purchase order with empty items", 400)
            
        po = await self.repo.create_purchase_order(po_data)
        
        # Emit outbox event procurement.created
        items_payload = [
            {"product_id": item.product_id, "quantity": item.quantity}
            for item in po.items
        ]
        await create_outbox_event(
            self.repo.db,
            "procurement.created",
            {
                "purchase_order_id": po.id,
                "supplier_name": po.supplier_name,
                "status": po.status,
                "items": items_payload
            }
        )
        
        return po

    async def auto_generate_draft_po(self, product_id: int, quantity: int) -> PurchaseOrder:
        """
        Called when inventory.low event is received.
        Creates a draft Purchase Order for the product.
        """
        po_data = PurchaseOrderCreate(
            supplier_name="AutoSupplier-Default",
            status="DRAFT",
            items=[
                PurchaseOrderItemCreate(product_id=product_id, quantity=quantity)
            ]
        )
        return await self.create_purchase_order(po_data)

    async def receive_purchase_order(self, po_id: int, store_id: int) -> PurchaseOrder:
        """
        Receives items from a PO and increments stock.
        """
        po = await self.get_purchase_order_by_id(po_id)
        if po.status == "RECEIVED":
            raise IMSException(f"Purchase Order {po_id} has already been received", 400)
        if po.status == "CANCELLED":
            raise IMSException(f"Purchase Order {po_id} is cancelled", 400)

        # Confirm reception
        await self.repo.update_purchase_order_status(po, "RECEIVED")

        # Increment stock in Inventory Service
        inv_service = InventoryService(self.repo.db)
        for item in po.items:
            # Add stock to inventory item. This will also automatically trigger inventory.updated outbox event.
            await inv_service.add_stock(
                store_id=store_id,
                product_id=item.product_id,
                quantity=item.quantity
            )

        return po
