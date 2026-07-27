import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import User, Role
from app.core.security import get_password_hash
from app.modules.notifications.service import NotificationService
from app.modules.notifications.schemas import NotificationBulkCreate


@pytest_asyncio.fixture
async def setup_users(db_session: AsyncSession):
    """Create test users with roles for notification tests."""
    # Create roles
    admin_role = Role(name="Admin", description="Administrator")
    viewer_role = Role(name="Viewer", description="Read-only access")
    db_session.add(admin_role)
    db_session.add(viewer_role)
    await db_session.flush()

    # Create admin user
    admin_user = User(
        username="notif_admin",
        email="notif_admin@test.com",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        roles=[admin_role],
    )
    db_session.add(admin_user)

    # Create regular user
    regular_user = User(
        username="notif_viewer",
        email="notif_viewer@test.com",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        roles=[viewer_role],
    )
    db_session.add(regular_user)

    # Create second regular user
    other_user = User(
        username="notif_other",
        email="notif_other@test.com",
        hashed_password=get_password_hash("testpassword"),
        is_active=True,
        roles=[viewer_role],
    )
    db_session.add(other_user)

    await db_session.commit()
    return admin_user, regular_user, other_user


@pytest_asyncio.fixture
async def setup_notifications(db_session: AsyncSession, setup_users):
    """Create test notifications for query and action tests."""
    admin_user, regular_user, _ = setup_users
    service = NotificationService(db_session)

    notif1 = await service.create_notification(
        user_id=regular_user.id,
        notification_type="SYSTEM",
        title="Welcome",
        message="Welcome to Accesco IMS",
        priority="LOW",
        actor_user_id=admin_user.id,
    )

    notif2 = await service.create_notification(
        user_id=regular_user.id,
        notification_type="INVENTORY_LOW",
        title="Low Stock Alert",
        message="Product MILK-AMUL-1L is below reorder level in Store 1",
        priority="HIGH",
        reference_type="inventory_item",
        reference_id="42",
        metadata_info={"store_id": 1, "product_sku": "MILK-AMUL-1L"},
        actor_user_id=admin_user.id,
    )

    notif3 = await service.create_notification(
        user_id=regular_user.id,
        notification_type="ORDER_STATUS",
        title="Order Confirmed",
        message="Order #101 has been confirmed",
        priority="NORMAL",
        reference_type="order",
        reference_id="101",
        actor_user_id=admin_user.id,
    )

    return notif1, notif2, notif3


# -------- Model + Service Unit Tests --------


@pytest.mark.asyncio
async def test_create_notification(db_session: AsyncSession, setup_users):
    """Test creating a single notification."""
    admin_user, regular_user, _ = setup_users
    service = NotificationService(db_session)

    notification = await service.create_notification(
        user_id=regular_user.id,
        notification_type="SYSTEM",
        title="Test Notification",
        message="This is a test notification",
        priority="NORMAL",
        actor_user_id=admin_user.id,
    )

    assert notification.id is not None
    assert notification.user_id == regular_user.id
    assert notification.type == "SYSTEM"
    assert notification.title == "Test Notification"
    assert notification.message == "This is a test notification"
    assert notification.priority == "NORMAL"
    assert notification.is_read is False


@pytest.mark.asyncio
async def test_create_notification_with_reference(db_session: AsyncSession, setup_users):
    """Test creating a notification with entity reference."""
    admin_user, regular_user, _ = setup_users
    service = NotificationService(db_session)

    notification = await service.create_notification(
        user_id=regular_user.id,
        notification_type="ORDER_STATUS",
        title="Order Shipped",
        message="Your order #123 has been shipped",
        priority="HIGH",
        reference_type="order",
        reference_id="123",
        metadata_info={"tracking_id": "TRK-456"},
        actor_user_id=admin_user.id,
    )

    assert notification.reference_type == "order"
    assert notification.reference_id == "123"
    assert notification.metadata_info == {"tracking_id": "TRK-456"}


@pytest.mark.asyncio
async def test_create_notification_invalid_type(db_session: AsyncSession, setup_users):
    """Test that invalid notification type raises IMSException."""
    admin_user, regular_user, _ = setup_users
    service = NotificationService(db_session)

    from app.core.exceptions import IMSException

    with pytest.raises(IMSException) as exc_info:
        await service.create_notification(
            user_id=regular_user.id,
            notification_type="INVALID_TYPE",
            title="Bad Type",
            message="Should fail",
            actor_user_id=admin_user.id,
        )
    assert "Invalid notification type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_notification_invalid_priority(db_session: AsyncSession, setup_users):
    """Test that invalid priority raises IMSException."""
    admin_user, regular_user, _ = setup_users
    service = NotificationService(db_session)

    from app.core.exceptions import IMSException

    with pytest.raises(IMSException) as exc_info:
        await service.create_notification(
            user_id=regular_user.id,
            notification_type="SYSTEM",
            title="Bad Priority",
            message="Should fail",
            priority="MEGA_URGENT",
            actor_user_id=admin_user.id,
        )
    assert "Invalid notification priority" in str(exc_info.value)


@pytest.mark.asyncio
async def test_create_bulk_notifications(db_session: AsyncSession, setup_users):
    """Test creating notifications for multiple users at once."""
    admin_user, regular_user, other_user = setup_users
    service = NotificationService(db_session)

    bulk_data = NotificationBulkCreate(
        user_ids=[regular_user.id, other_user.id],
        type="SYSTEM",
        priority="NORMAL",
        title="System Maintenance",
        message="The system will be down for maintenance tonight",
    )

    notifications = await service.create_bulk_notifications(
        bulk_data, actor_user_id=admin_user.id
    )

    assert len(notifications) == 2
    user_ids = {n.user_id for n in notifications}
    assert regular_user.id in user_ids
    assert other_user.id in user_ids
    for n in notifications:
        assert n.title == "System Maintenance"
        assert n.is_read is False


@pytest.mark.asyncio
async def test_get_user_notifications_paginated(db_session: AsyncSession, setup_users, setup_notifications):
    """Test paginated notification retrieval."""
    _, regular_user, _ = setup_users
    service = NotificationService(db_session)

    items, total, unread_count = await service.get_user_notifications(
        user_id=regular_user.id, skip=0, limit=2
    )

    assert total == 3
    assert len(items) == 2
    assert unread_count == 3  # All unread


@pytest.mark.asyncio
async def test_get_user_notifications_filtered_by_type(db_session: AsyncSession, setup_users, setup_notifications):
    """Test notification filtering by type."""
    _, regular_user, _ = setup_users
    service = NotificationService(db_session)

    items, total, _ = await service.get_user_notifications(
        user_id=regular_user.id, notification_type="INVENTORY_LOW"
    )

    assert total == 1
    assert items[0].type == "INVENTORY_LOW"
    assert items[0].title == "Low Stock Alert"


@pytest.mark.asyncio
async def test_get_user_notifications_filtered_by_priority(db_session: AsyncSession, setup_users, setup_notifications):
    """Test notification filtering by priority."""
    _, regular_user, _ = setup_users
    service = NotificationService(db_session)

    items, total, _ = await service.get_user_notifications(
        user_id=regular_user.id, priority="HIGH"
    )

    assert total == 1
    assert items[0].priority == "HIGH"


@pytest.mark.asyncio
async def test_get_unread_count(db_session: AsyncSession, setup_users, setup_notifications):
    """Test unread count retrieval."""
    _, regular_user, _ = setup_users
    service = NotificationService(db_session)

    count = await service.get_unread_count(regular_user.id)
    assert count == 3


@pytest.mark.asyncio
async def test_mark_as_read(db_session: AsyncSession, setup_users, setup_notifications):
    """Test marking a single notification as read."""
    _, regular_user, _ = setup_users
    notif1, _, _ = setup_notifications
    service = NotificationService(db_session)

    updated = await service.mark_as_read(notif1.id, regular_user.id)
    assert updated.is_read is True

    # Unread count should decrease
    count = await service.get_unread_count(regular_user.id)
    assert count == 2


@pytest.mark.asyncio
async def test_mark_as_read_idempotent(db_session: AsyncSession, setup_users, setup_notifications):
    """Test that marking an already-read notification is idempotent."""
    _, regular_user, _ = setup_users
    notif1, _, _ = setup_notifications
    service = NotificationService(db_session)

    # Mark read first time
    await service.mark_as_read(notif1.id, regular_user.id)
    # Mark read second time (should not error)
    updated = await service.mark_as_read(notif1.id, regular_user.id)
    assert updated.is_read is True


@pytest.mark.asyncio
async def test_mark_multiple_as_read(db_session: AsyncSession, setup_users, setup_notifications):
    """Test marking multiple notifications as read."""
    _, regular_user, _ = setup_users
    notif1, notif2, _ = setup_notifications
    service = NotificationService(db_session)

    updated_count = await service.mark_multiple_as_read(
        [notif1.id, notif2.id], regular_user.id
    )
    assert updated_count == 2

    count = await service.get_unread_count(regular_user.id)
    assert count == 1


@pytest.mark.asyncio
async def test_mark_all_as_read(db_session: AsyncSession, setup_users, setup_notifications):
    """Test marking all notifications as read."""
    _, regular_user, _ = setup_users
    service = NotificationService(db_session)

    updated_count = await service.mark_all_as_read(regular_user.id)
    assert updated_count == 3

    count = await service.get_unread_count(regular_user.id)
    assert count == 0


@pytest.mark.asyncio
async def test_delete_notification(db_session: AsyncSession, setup_users, setup_notifications):
    """Test deleting a single notification."""
    _, regular_user, _ = setup_users
    notif1, _, _ = setup_notifications
    service = NotificationService(db_session)

    await service.delete_notification(notif1.id, regular_user.id)

    from app.core.exceptions import ResourceNotFoundException

    with pytest.raises(ResourceNotFoundException):
        await service.get_notification_by_id(notif1.id, regular_user.id)


@pytest.mark.asyncio
async def test_delete_all_read(db_session: AsyncSession, setup_users, setup_notifications):
    """Test deleting all read notifications."""
    _, regular_user, _ = setup_users
    service = NotificationService(db_session)

    # Mark two as read first
    notif1, notif2, _ = setup_notifications
    await service.mark_as_read(notif1.id, regular_user.id)
    await service.mark_as_read(notif2.id, regular_user.id)

    deleted_count = await service.delete_all_read(regular_user.id)
    assert deleted_count == 2

    # Only one notification should remain
    items, total, _ = await service.get_user_notifications(user_id=regular_user.id)
    assert total == 1


@pytest.mark.asyncio
async def test_ownership_enforcement(db_session: AsyncSession, setup_users, setup_notifications):
    """Test that users cannot access other users' notifications."""
    _, _, other_user = setup_users
    notif1, _, _ = setup_notifications  # belongs to regular_user
    service = NotificationService(db_session)

    from app.core.exceptions import ForbiddenException

    with pytest.raises(ForbiddenException):
        await service.get_notification_by_id(notif1.id, other_user.id)


@pytest.mark.asyncio
async def test_ownership_enforcement_on_mark_read(db_session: AsyncSession, setup_users, setup_notifications):
    """Test that users cannot mark other users' notifications as read."""
    _, _, other_user = setup_users
    notif1, _, _ = setup_notifications
    service = NotificationService(db_session)

    from app.core.exceptions import ForbiddenException

    with pytest.raises(ForbiddenException):
        await service.mark_as_read(notif1.id, other_user.id)


@pytest.mark.asyncio
async def test_ownership_enforcement_on_delete(db_session: AsyncSession, setup_users, setup_notifications):
    """Test that users cannot delete other users' notifications."""
    _, _, other_user = setup_users
    notif1, _, _ = setup_notifications
    service = NotificationService(db_session)

    from app.core.exceptions import ForbiddenException

    with pytest.raises(ForbiddenException):
        await service.delete_notification(notif1.id, other_user.id)


@pytest.mark.asyncio
async def test_not_found_notification(db_session: AsyncSession, setup_users):
    """Test that accessing a non-existent notification raises 404."""
    _, regular_user, _ = setup_users
    service = NotificationService(db_session)

    from app.core.exceptions import ResourceNotFoundException

    with pytest.raises(ResourceNotFoundException):
        await service.get_notification_by_id(99999, regular_user.id)


@pytest.mark.asyncio
async def test_filtered_by_read_status(db_session: AsyncSession, setup_users, setup_notifications):
    """Test filtering notifications by read status."""
    _, regular_user, _ = setup_users
    notif1, _, _ = setup_notifications
    service = NotificationService(db_session)

    # Mark one as read
    await service.mark_as_read(notif1.id, regular_user.id)

    # Filter unread
    items, total, _ = await service.get_user_notifications(
        user_id=regular_user.id, is_read=False
    )
    assert total == 2

    # Filter read
    items, total, _ = await service.get_user_notifications(
        user_id=regular_user.id, is_read=True
    )
    assert total == 1
    assert items[0].id == notif1.id


@pytest.mark.asyncio
async def test_notification_ordering(db_session: AsyncSession, setup_users, setup_notifications):
    """Test that notifications are returned in descending chronological order."""
    _, regular_user, _ = setup_users
    service = NotificationService(db_session)

    items, _, _ = await service.get_user_notifications(user_id=regular_user.id)

    # Most recent first
    for i in range(len(items) - 1):
        assert items[i].created_at >= items[i + 1].created_at
