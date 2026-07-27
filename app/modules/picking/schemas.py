from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class PickTaskItemBase(BaseModel):
    order_item_id: int
    product_id: int
    expected_quantity: int
    picked_quantity: int = 0

class PickTaskItemResponse(PickTaskItemBase):
    id: int
    pick_task_id: int

    model_config = ConfigDict(from_attributes=True)

class PickTaskBase(BaseModel):
    wave_id: int
    order_id: int
    assigned_to: Optional[int] = None
    status: str

class PickTaskResponse(PickTaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    items: List[PickTaskItemResponse] = []

    model_config = ConfigDict(from_attributes=True)

class PickWaveBase(BaseModel):
    store_id: int
    status: str

class PickWaveResponse(PickWaveBase):
    id: int
    created_at: datetime
    updated_at: datetime
    tasks: List[PickTaskResponse] = []

    model_config = ConfigDict(from_attributes=True)

class PickActionRequest(BaseModel):
    quantity: int = Field(..., gt=0, description="Quantity picked")
