from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DispatchResponse(BaseModel):
    order_id: int
    rider_id: int
    status: str


class DispatchStatusResponse(BaseModel):
    """Response for dispatch lifecycle status transitions."""
    order_id: int
    rider_id: Optional[int] = None
    order_status: str
    rider_status: Optional[str] = None
    message: str
    timestamp: str