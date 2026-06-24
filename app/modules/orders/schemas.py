# app/modules/orders/schemas.py
from __future__ import annotations

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
    
    # Phase 2 Coordinates (Section 03)
    latitude: float
    longitude: float

class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    store_id: int
    
    # Coordinates provided during checkout
    latitude: float
    longitude: float

class OrderResponse(OrderBase):
    id: int
    created_at: datetime
    
    # SLA metrics calculated upon creation (Section 04)
    delivery_zone: str
    sla_deadline: datetime
    assignment_status: str
    
    items: List[OrderItemResponse]
    model_config = ConfigDict(from_attributes=True)