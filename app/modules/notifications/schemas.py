from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import Optional, Dict, Any, List


# Valid notification types and priorities
NOTIFICATION_TYPES = {
    "INVENTORY_LOW",
    "ORDER_STATUS",
    "PAYMENT",
    "SYSTEM",
    "WAREHOUSE",
    "TRANSFER",
    "PROCUREMENT",
    "DISPATCH",
    "REPLENISHMENT",
}

NOTIFICATION_PRIORITIES = {"LOW", "NORMAL", "HIGH", "CRITICAL"}


class NotificationBase(BaseModel):
    type: str = Field(..., min_length=1, max_length=50)
    priority: str = Field(default="NORMAL", max_length=20)
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=1000)
    reference_type: Optional[str] = Field(default=None, max_length=100)
    reference_id: Optional[str] = Field(default=None, max_length=255)
    metadata_info: Optional[Dict[str, Any]] = None


class NotificationCreate(NotificationBase):
    """Schema for creating a notification. user_id is provided by the service layer."""
    model_config = ConfigDict(extra="forbid")

    user_id: int


class NotificationBulkCreate(BaseModel):
    """Schema for creating notifications for multiple users at once."""
    model_config = ConfigDict(extra="forbid")

    user_ids: List[int] = Field(..., min_length=1)
    type: str = Field(..., min_length=1, max_length=50)
    priority: str = Field(default="NORMAL", max_length=20)
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=1000)
    reference_type: Optional[str] = Field(default=None, max_length=100)
    reference_id: Optional[str] = Field(default=None, max_length=255)
    metadata_info: Optional[Dict[str, Any]] = None


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    priority: str
    title: str
    message: str
    is_read: bool
    reference_type: Optional[str] = None
    reference_id: Optional[str] = None
    metadata_info: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    """Paginated response wrapper for notification lists."""
    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    skip: int
    limit: int


class NotificationMarkReadRequest(BaseModel):
    """Schema for marking specific notifications as read."""
    model_config = ConfigDict(extra="forbid")

    notification_ids: List[int] = Field(..., min_length=1)


class NotificationUnreadCountResponse(BaseModel):
    """Response with the count of unread notifications."""
    unread_count: int
