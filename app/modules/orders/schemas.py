from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional
from app.modules.products.schemas import ProductResponse

class OrderItemBase(BaseModel):
    product_id: int
    quantity: int
    price: float

class OrderItemCreate(OrderItemBase):
    pass

class OrderItemResponse(OrderItemBase):
    id: int
    product: ProductResponse
    model_config = ConfigDict(from_attributes=True)

class OrderBase(BaseModel):
    customer_id: int
    store_id: int
    status: str = "PENDING"
    total_amount: float
    payment_status: str = "PENDING"

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    # For order placement, we can optionally supply a store_id if checking out for a specific store, or we check dynamically.
    store_id: int

class OrderResponse(OrderBase):
    id: int
    created_at: datetime
    items: List[OrderItemResponse]
    model_config = ConfigDict(from_attributes=True)
