from pydantic import BaseModel
from typing import Optional


class OrderCreatedEvent(BaseModel):
    order_id: str
    store_id: Optional[int] = None
    total_amount: Optional[float] = None


class OrderUpdatedEvent(BaseModel):
    order_id: str
    status: str


class PaymentConfirmedEvent(BaseModel):
    order_id: str


class InventoryUpdatedEvent(BaseModel):
    product_id: int
    available_quantity: int
    store_id: Optional[int] = None


class InventoryLowEvent(BaseModel):
    product_id: int
    available_quantity: int


class ShipmentDeliveredEvent(BaseModel):
    order_id: str
    store_id: Optional[int] = None


class OrderCancelledEvent(BaseModel):
    order_id: str
