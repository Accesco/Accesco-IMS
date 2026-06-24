# app/modules/stores/schemas.py
from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Optional

class StoreBase(BaseModel):
    name: str
    address: str
    city: str
    state: str
    active: Optional[bool] = True
    
    # Coordinate Inputs (Optional on Base, can be supplied on create/update)
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class StoreCreate(StoreBase):
    pass

class StoreUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    active: Optional[bool] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class StoreResponse(StoreBase):
    id: int
    model_config = ConfigDict(from_attributes=True)