from pydantic import BaseModel, ConfigDict
from typing import Optional

class StoreBase(BaseModel):
    name: str
    address: str
    city: str
    state: str
    active: Optional[bool] = True

class StoreCreate(StoreBase):
    pass

class StoreUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    active: Optional[bool] = None

class StoreResponse(StoreBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
