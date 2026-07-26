from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.modules.auth.routes import get_current_user, RoleChecker
from app.models.auth import User
from app.modules.notifications.schemas import (
    NotificationResponse,
    NotificationListResponse,
    NotificationCreate,
    NotificationBulkCreate,
    NotificationMarkReadRequest,
    NotificationUnreadCountResponse,
)
from app.modules.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])

# Role guards
admin_only = RoleChecker(["Admin"])
all_authenticated = RoleChecker(
    ["Admin", "StoreManager", "ProcurementManager", "InventoryManager", "Viewer"]
)


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    is_read: Optional[bool] = None,
    type: Optional[str] = Query(None, alias="type"),
    priority: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(all_authenticated),
):
    """Retrieve paginated notifications for the authenticated user."""
    service = NotificationService(db)
    items, total, unread_count = await service.get_user_notifications(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        is_read=is_read,
        notification_type=type,
        priority=priority,
    )
    return NotificationListResponse(
        notifications=items,
        total=total,
        unread_count=unread_count,
        skip=skip,
        limit=limit,
    )


@router.get("/unread-count", response_model=NotificationUnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(all_authenticated),
):
    """Get the count of unread notifications for the authenticated user."""
    service = NotificationService(db)
    count = await service.get_unread_count(current_user.id)
    return NotificationUnreadCountResponse(unread_count=count)


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(all_authenticated),
):
    """Get a specific notification by ID. Only the notification owner can access it."""
    service = NotificationService(db)
    return await service.get_notification_by_id(notification_id, current_user.id)


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    data: NotificationCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(admin_only),
):
    """Create a notification for a specific user. Admin only."""
    service = NotificationService(db)
    return await service.create_notification(
        user_id=data.user_id,
        notification_type=data.type,
        title=data.title,
        message=data.message,
        priority=data.priority,
        reference_type=data.reference_type,
        reference_id=data.reference_id,
        metadata_info=data.metadata_info,
        actor_user_id=_current_user.id,
    )


@router.post("/bulk", response_model=List[NotificationResponse], status_code=status.HTTP_201_CREATED)
async def create_bulk_notifications(
    data: NotificationBulkCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(admin_only),
):
    """Create the same notification for multiple users. Admin only."""
    service = NotificationService(db)
    return await service.create_bulk_notifications(data, actor_user_id=_current_user.id)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(all_authenticated),
):
    """Mark a single notification as read."""
    service = NotificationService(db)
    return await service.mark_as_read(notification_id, current_user.id)


@router.patch("/read", status_code=status.HTTP_200_OK)
async def mark_multiple_notifications_read(
    data: NotificationMarkReadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(all_authenticated),
):
    """Mark multiple notifications as read by providing their IDs."""
    service = NotificationService(db)
    updated_count = await service.mark_multiple_as_read(data.notification_ids, current_user.id)
    return {"updated_count": updated_count}


@router.patch("/read-all", status_code=status.HTTP_200_OK)
async def mark_all_notifications_read(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(all_authenticated),
):
    """Mark all unread notifications as read for the authenticated user."""
    service = NotificationService(db)
    updated_count = await service.mark_all_as_read(current_user.id)
    return {"updated_count": updated_count}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(all_authenticated),
):
    """Delete a single notification. Only the notification owner can delete it."""
    service = NotificationService(db)
    await service.delete_notification(notification_id, current_user.id)


@router.delete("/read", status_code=status.HTTP_200_OK)
async def delete_all_read_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(all_authenticated),
):
    """Delete all read notifications for the authenticated user."""
    service = NotificationService(db)
    deleted_count = await service.delete_all_read(current_user.id)
    return {"deleted_count": deleted_count}
