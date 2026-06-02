from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
from app.modules.products.schemas import ProductResponse

class PurchaseOrderItemBase(BaseModel):
    product_id: int
    quantity: int

class PurchaseOrderItemCreate(PurchaseOrderItemBase):
    pass

class PurchaseOrderItemResponse(PurchaseOrderItemBase):
    id: int
    product: ProductResponse
    model_config = ConfigDict(from_attributes=True)

class PurchaseOrderBase(BaseModel):
    supplier_name: str
    status: str = "DRAFT"

class PurchaseOrderCreate(PurchaseOrderBase):
    items: List[PurchaseOrderItemCreate]

class PurchaseOrderResponse(PurchaseOrderBase):
    id: int
    created_at: datetime
    items: List[PurchaseOrderItemResponse]
    model_config = ConfigDict(from_attributes=True)
