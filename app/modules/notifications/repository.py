from __future__ import annotations

from typing import Optional, List, Tuple
from datetime import datetime
from sqlalchemy import select, desc, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification
from app.modules.notifications.schemas import NotificationCreate


class NotificationRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(self, data: NotificationCreate) -> Notification:
        db_notification = Notification(
            user_id=data.user_id,
            type=data.type,
            priority=data.priority,
            title=data.title,
            message=data.message,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
            metadata_info=data.metadata_info,
        )
        self.db.add(db_notification)
        await self.db.flush()
        return db_notification

    async def create_bulk(self, notifications: List[NotificationCreate]) -> List[Notification]:
        db_notifications = [
            Notification(
                user_id=data.user_id,
                type=data.type,
                priority=data.priority,
                title=data.title,
                message=data.message,
                reference_type=data.reference_type,
                reference_id=data.reference_id,
                metadata_info=data.metadata_info,
            )
            for data in notifications
        ]
        self.db.add_all(db_notifications)
        await self.db.flush()
        return db_notifications

    async def get_by_id(self, notification_id: int) -> Optional[Notification]:
        result = await self.db.execute(
            select(Notification).where(Notification.id == notification_id)
        )
        return result.scalar_one_or_none()

    async def get_notifications(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 50,
        is_read: Optional[bool] = None,
        notification_type: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Tuple[List[Notification], int]:
        """Retrieve paginated notifications for a user with optional filters. Returns (items, total_count)."""
        query = select(Notification).where(Notification.user_id == user_id)
        count_query = select(func.count(Notification.id)).where(Notification.user_id == user_id)

        if is_read is not None:
            query = query.where(Notification.is_read == is_read)
            count_query = count_query.where(Notification.is_read == is_read)
        if notification_type is not None:
            query = query.where(Notification.type == notification_type)
            count_query = count_query.where(Notification.type == notification_type)
        if priority is not None:
            query = query.where(Notification.priority == priority)
            count_query = count_query.where(Notification.priority == priority)

        # Total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Paginated items
        query = query.order_by(desc(Notification.created_at)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_unread_count(self, user_id: int) -> int:
        result = await self.db.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
        )
        return result.scalar() or 0

    async def mark_as_read(self, notification: Notification) -> Notification:
        notification.is_read = True
        await self.db.flush()
        return notification

    async def mark_multiple_as_read(self, notification_ids: List[int], user_id: int) -> int:
        """Mark multiple notifications as read for a specific user. Returns count of updated rows."""
        stmt = (
            update(Notification)
            .where(
                Notification.id.in_(notification_ids),
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .values(is_read=True)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all unread notifications as read for a user. Returns count of updated rows."""
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .values(is_read=True)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def delete_notification(self, notification: Notification) -> bool:
        await self.db.delete(notification)
        await self.db.flush()
        return True

    async def delete_all_read(self, user_id: int) -> int:
        """Delete all read notifications for a user. Returns count of deleted rows."""
        stmt = (
            delete(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == True,
            )
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount
