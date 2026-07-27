from __future__ import annotations

import logging
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundException, ForbiddenException, IMSException
from app.models.notification import Notification
from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.schemas import (
    NotificationCreate,
    NotificationBulkCreate,
    NOTIFICATION_TYPES,
    NOTIFICATION_PRIORITIES,
)
from app.modules.audit.service import AuditLogService
from app.modules.websocket.events import publish_event

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.repo = NotificationRepository(db)
        self.db = db

    def _validate_type_and_priority(self, notification_type: str, priority: str) -> None:
        """Validates notification type and priority against allowed values."""
        if notification_type not in NOTIFICATION_TYPES:
            raise IMSException(
                f"Invalid notification type: '{notification_type}'. "
                f"Allowed types: {', '.join(sorted(NOTIFICATION_TYPES))}",
                400,
            )
        if priority not in NOTIFICATION_PRIORITIES:
            raise IMSException(
                f"Invalid notification priority: '{priority}'. "
                f"Allowed priorities: {', '.join(sorted(NOTIFICATION_PRIORITIES))}",
                400,
            )

    async def create_notification(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        message: str,
        priority: str = "NORMAL",
        reference_type: Optional[str] = None,
        reference_id: Optional[str] = None,
        metadata_info: Optional[Dict[str, Any]] = None,
        actor_user_id: Optional[int] = None,
    ) -> Notification:
        """
        Creates a single notification for a user.
        This is the primary method that other modules should call to generate notifications.
        Publishes a real-time WebSocket event after commit.
        """
        self._validate_type_and_priority(notification_type, priority)

        data = NotificationCreate(
            user_id=user_id,
            type=notification_type,
            priority=priority,
            title=title,
            message=message,
            reference_type=reference_type,
            reference_id=reference_id,
            metadata_info=metadata_info,
        )

        notification = await self.repo.create_notification(data)

        await AuditLogService(self.db).log_action(
            module="Notifications",
            action="CREATE_NOTIFICATION",
            user_id=actor_user_id,
            entity_id=str(notification.id),
            new_values={
                "type": notification_type,
                "priority": priority,
                "title": title,
                "user_id": user_id,
            },
        )

        await self.db.commit()

        # Publish real-time WebSocket event after successful commit
        await publish_event(
            event_type="NOTIFICATION_CREATED",
            entity_type="notification",
            entity_id=notification.id,
            data={
                "notification_id": notification.id,
                "user_id": user_id,
                "type": notification_type,
                "priority": priority,
                "title": title,
                "message": message,
                "reference_type": reference_type,
                "reference_id": reference_id,
                "is_read": False,
            },
        )

        return notification

    async def create_bulk_notifications(
        self,
        bulk_data: NotificationBulkCreate,
        actor_user_id: Optional[int] = None,
    ) -> List[Notification]:
        """Creates the same notification for multiple users."""
        self._validate_type_and_priority(bulk_data.type, bulk_data.priority)

        create_items = [
            NotificationCreate(
                user_id=uid,
                type=bulk_data.type,
                priority=bulk_data.priority,
                title=bulk_data.title,
                message=bulk_data.message,
                reference_type=bulk_data.reference_type,
                reference_id=bulk_data.reference_id,
                metadata_info=bulk_data.metadata_info,
            )
            for uid in bulk_data.user_ids
        ]

        notifications = await self.repo.create_bulk(create_items)

        await AuditLogService(self.db).log_action(
            module="Notifications",
            action="CREATE_BULK_NOTIFICATIONS",
            user_id=actor_user_id,
            new_values={
                "type": bulk_data.type,
                "priority": bulk_data.priority,
                "title": bulk_data.title,
                "user_count": len(bulk_data.user_ids),
            },
        )

        await self.db.commit()

        # Publish real-time event for each recipient
        for notification in notifications:
            await publish_event(
                event_type="NOTIFICATION_CREATED",
                entity_type="notification",
                entity_id=notification.id,
                data={
                    "notification_id": notification.id,
                    "user_id": notification.user_id,
                    "type": notification.type,
                    "priority": notification.priority,
                    "title": notification.title,
                    "message": notification.message,
                    "is_read": False,
                },
            )

        return notifications

    async def get_notification_by_id(
        self, notification_id: int, current_user_id: int
    ) -> Notification:
        """Get a notification by ID, enforcing ownership."""
        notification = await self.repo.get_by_id(notification_id)
        if not notification:
            raise ResourceNotFoundException(f"Notification with ID {notification_id} not found")
        if notification.user_id != current_user_id:
            raise ForbiddenException("You do not have permission to access this notification")
        return notification

    async def get_user_notifications(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        is_read: Optional[bool] = None,
        notification_type: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Tuple[List[Notification], int, int]:
        """
        Retrieve paginated notifications for a user.
        Returns (notifications, total_count, unread_count).
        """
        items, total = await self.repo.get_notifications(
            user_id=user_id,
            skip=skip,
            limit=limit,
            is_read=is_read,
            notification_type=notification_type,
            priority=priority,
        )
        unread_count = await self.repo.get_unread_count(user_id)
        return items, total, unread_count

    async def get_unread_count(self, user_id: int) -> int:
        """Get the count of unread notifications for a user."""
        return await self.repo.get_unread_count(user_id)

    async def mark_as_read(
        self, notification_id: int, current_user_id: int
    ) -> Notification:
        """Mark a single notification as read, enforcing ownership."""
        notification = await self.get_notification_by_id(notification_id, current_user_id)

        if notification.is_read:
            return notification

        old_read = notification.is_read
        notification = await self.repo.mark_as_read(notification)

        await AuditLogService(self.db).log_action(
            module="Notifications",
            action="MARK_READ",
            user_id=current_user_id,
            entity_id=str(notification_id),
            old_values={"is_read": old_read},
            new_values={"is_read": True},
        )

        await self.db.commit()
        return notification

    async def mark_multiple_as_read(
        self, notification_ids: List[int], current_user_id: int
    ) -> int:
        """Mark multiple notifications as read for the current user."""
        updated_count = await self.repo.mark_multiple_as_read(notification_ids, current_user_id)

        if updated_count > 0:
            await AuditLogService(self.db).log_action(
                module="Notifications",
                action="MARK_MULTIPLE_READ",
                user_id=current_user_id,
                new_values={"notification_ids": notification_ids, "updated_count": updated_count},
            )

        await self.db.commit()
        return updated_count

    async def mark_all_as_read(self, current_user_id: int) -> int:
        """Mark all unread notifications as read for the current user."""
        updated_count = await self.repo.mark_all_as_read(current_user_id)

        if updated_count > 0:
            await AuditLogService(self.db).log_action(
                module="Notifications",
                action="MARK_ALL_READ",
                user_id=current_user_id,
                new_values={"updated_count": updated_count},
            )

        await self.db.commit()
        return updated_count

    async def delete_notification(
        self, notification_id: int, current_user_id: int
    ) -> None:
        """Delete a notification, enforcing ownership."""
        notification = await self.get_notification_by_id(notification_id, current_user_id)

        await self.repo.delete_notification(notification)

        await AuditLogService(self.db).log_action(
            module="Notifications",
            action="DELETE_NOTIFICATION",
            user_id=current_user_id,
            entity_id=str(notification_id),
            old_values={
                "type": notification.type,
                "title": notification.title,
            },
        )

        await self.db.commit()

    async def delete_all_read(self, current_user_id: int) -> int:
        """Delete all read notifications for the current user."""
        deleted_count = await self.repo.delete_all_read(current_user_id)

        if deleted_count > 0:
            await AuditLogService(self.db).log_action(
                module="Notifications",
                action="DELETE_ALL_READ",
                user_id=current_user_id,
                new_values={"deleted_count": deleted_count},
            )

        await self.db.commit()
        return deleted_count
