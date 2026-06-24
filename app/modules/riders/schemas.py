from pydantic import BaseModel, ConfigDict
from typing import Optional


class RiderBase(BaseModel):
    name: str
    phone: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_available: bool = True
    status: str = "IDLE"


class RiderCreate(RiderBase):
    pass


class RiderUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_available: Optional[bool] = None
    status: Optional[str] = None


class RiderResponse(RiderBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True
    )