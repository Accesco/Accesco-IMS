from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class InventoryItemBase(BaseModel):
    store_id: int
    product_id: int
    available_quantity: int
    reserved_quantity: int = 0
    reorder_level: int = 10

class InventoryItemCreate(InventoryItemBase):
    pass

class InventoryItemUpdate(BaseModel):
    available_quantity: Optional[int] = None
    reserved_quantity: Optional[int] = None
    reorder_level: Optional[int] = None

class InventoryItemResponse(InventoryItemBase):
    id: int
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class InventoryReservationBase(BaseModel):
    order_id: Optional[str] = None
    store_id: int
    product_id: int
    quantity: int
    status: str = "PENDING"
    expires_at: datetime

class InventoryReservationCreate(BaseModel):
    store_id: int
    product_id: int
    quantity: int
    order_id: Optional[str] = None
    expires_in_seconds: Optional[int] = 300  # Default 5 minutes

class InventoryReservationResponse(InventoryReservationBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
