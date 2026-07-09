from enum import Enum
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class RiderStatus(str, Enum):
    IDLE = "IDLE"
    ASSIGNED = "ASSIGNED"
    EN_ROUTE_PICKUP = "EN_ROUTE_PICKUP"
    DELIVERING = "  "
    RETURNING = "RETURNING"
    OFFLINE = "OFFLINE"

class RiderBase(BaseModel):
    name: str
    phone: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_available: bool = True
    status: RiderStatus = RiderStatus.IDLE
    last_heartbeat_at: Optional[datetime] = None


class RiderCreate(RiderBase):
    pass


class RiderUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_available: Optional[bool] = None
    status: Optional[RiderStatus] = None


class RiderResponse(RiderBase):
    id: int

    model_config = ConfigDict(
        from_attributes=True
    )

class RiderHeartbeat(BaseModel):
    latitude: float
    longitude: float
    battery_level: float