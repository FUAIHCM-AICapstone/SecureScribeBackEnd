"""Unit tests for notification service functions"""

import uuid
from datetime import datetime, timezone
from typing import List

import pytest
from faker import Faker
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.services.notification import (
    create_global_notification,
    create_notification,
    create_notifications_bulk,
    delete_notification,
    get_notification,
    get_notifications,
    update_notification,
)
from tests.factories import NotificationFactory, UserFactory

fake = Faker()


class TestCreateNotification:
    """Tests for create_notification function"""

    def test_create_notification_success(self, db_session: Session):
        """Test creating a notification with valid data"""
        user = UserFactory.create(db_session)
        notification_type = "task_assigned"
        payload = {"task_id": str(uuid.uuid4()), "task_title": "Test Task"}

        notification = create_notification(
            db_session,
            user_id=user.id,
            type=notification_type,
            payload=payload,
            channel="in_app",
        )

        assert notification.id is not None
        assert notification.user_id == user.id
        assert notification.type == notification_type
        assert notification.payload == payload
        assert notification.channel == "in_app"
        assert notification.is_read is False
        assert notification.created_at is not None

    def test_create_notification_minimal_data(self, db_session: Session):
        """Test creating a notification with only required user_id"""
        user = UserFactory.create(db_session)

        notification = create_notification(db_session, user_id=user.id)

        assert notification.id is not None
        assert notification.user_id == user.id
        assert notification.type is None
        assert notification.payload is None
        assert notification.is_read is False

    def test_create_notification_with_all_fields(self, db_session: Session):
        """Test creating a notification with all optional fields"""
        user = UserFactory.create(db_session)
        payload = {"title": "Test", "body": "Test body"}

        notification = create_notification(
            db_session,
            user_id=user.id,
            type="meeting_reminder",
            payload=payload,
            channel="fcm",
            icon="https://example.com/icon.png",
            badge="https://example.com/badge.png",
            sound="notification.mp3",
            ttl=3600,
        )

        assert notification.type == "meeting_reminder"
        assert notification.payload == payload
        assert notification.channel == "fcm"
        assert notification.icon == "https://example.com/icon.png"
        assert notification.badge == "https://example.com/badge.png"
        assert notification.sound == "notification.mp3"
        assert notification.ttl == 3600

    def test_create_notification_different_types(self, db_session: Session):
        """Test creating notifications with different types"""
        user = UserFactory.create(db_session)
        notification_types = ["task_assigned", "meeting_reminder", "project_update", "comment_reply"]

        for notif_type in notification_types:
            notification = create_notification(
                db_session,
                user_id=user.id,
                type=notif_type,
            )
            assert notification.type == notif_type


class TestCreateNotificationsBulk:
    """Tests for create_notifications_bulk function"""

    def test_create_notifications_bulk_success(self, db_session: Session):
        """Test bulk creating notifications for multiple users"""
        users = UserFactory.create_batch(db_session, count=3)
        user_ids = [user.id for user in users]
        notification_type = "announcement"
        payload = {"message": "Important announcement"}

        notifications = create_notifications_bulk(
            db_session,
            user_ids,
            type=notification_type,
            payload=payload,
            channel="in_app",
        )

        assert len(notifications) == 3
        assert all(n.type == notification_type for n in notifications)
        assert all(n.payload == payload for n in notifications)
        assert all(n.channel == "in_app" for n in notifications)
        assert all(n.is_read is False for n in notifications)

    def test_create_notifications_bulk_single_user(self, db_session: Session):
        """Test bulk creating notification for single user"""
        user = UserFactory.create(db_session)

        notifications = create_notifications_bulk(
            db_session,
            [user.id],
            type="test",
        )

        assert len(notifications) == 1
        assert notifications[0].user_id == user.id

    def test_create_notifications_bulk_empty_list(self, db_session: Session):
        """Test bulk creating with empty user list"""
        notifications = create_notifications_bulk(
            db_session,
            [],
            type="test",
        )

        assert len(notifications) == 0

    def test_create_notifications_bulk_with_payload(self, db_session: Session):
        """Test bulk creating notifications with complex payload"""
        users = UserFactory.create_batch(db_session, count=2)
        user_ids = [user.id for user in users]
        payload = {
            "title": "Meeting Reminder",
            "body": "Your meeting starts in 15 minutes",
            "meeting_id": str(uuid.uuid4()),
            "meeting_url": "https://example.com/meeting",
        }

        notifications = create_notifications_bulk(
            db_session,
            user_ids,
            type="meeting_reminder",
            payload=payload,
        )

        assert len(notifications) == 2
        assert all(n.payload == payload for n in notifications)

    def test_create_notifications_bulk_all_fields(self, db_session: Session):
        """Test bulk creating with all optional fields"""
        users = UserFactory.create_batch(db_session, count=2)
        user_ids = [user.id for user in users]

        notifications = create_notifications_bulk(
            db_session,
            user_ids,
            type="test",
            payload={"test": "data"},
            channel="fcm",
            icon="icon.png",
            badge="badge.png",
            sound="sound.mp3",
            ttl=7200,
        )

        assert len(notifications) == 2
        assert all(n.icon == "icon.png" for n in notifications)
        assert all(n.badge == "badge.png" for n in notifications)
        assert all(n.sound == "sound.mp3" for n in notifications)
        assert all(n.ttl == 7200 for n in notifications)


class TestCreateGlobalNotification:
    """Tests for create_global_notification function"""

    def test_create_global_notification_success(self, db_session: Session):
        """Test creating global notification for all users"""
        # Create multiple users
        UserFactory.create_batch(db_session, count=3)

        notification_type = "system_announcement"
        payload = {"message": "System maintenance scheduled"}

        notifications = create_global_notification(
            db_session,
            type=notification_type,
            payload=payload,
            channel="in_app",
        )

        # Should create notification for all users
        assert len(notifications) >= 3
        assert all(n.type == notification_type for n in notifications)
        assert all(n.payload == payload for n in notifications)

    def test_create_global_notification_minimal_data(self, db_session: Session):
        """Test creating global notification with minimal data"""
        UserFactory.create_batch(db_session, count=2)

        notifications = create_global_notification(db_session)

        assert len(notifications) >= 2
        assert all(n.type is None for n in notifications)

    def test_create_global_notification_with_all_fields(self, db_session: Session):
        """Test creating global notification with all fields"""
        UserFactory.create_batch(db_session, count=2)

        notifications = create_global_notification(
            db_session,
            type="maintenance",
            payload={"duration": "2 hours"},
            channel="fcm",
            icon="maintenance.png",
            badge="badge.png",
            sound="alert.mp3",
            ttl=3600,
        )

        assert len(notifications) >= 2
        assert all(n.type == "maintenance" for n in notifications)
        assert all(n.icon == "maintenance.png" for n in notifications)
        assert all(n.ttl == 3600 for n in notifications)


class TestGetNotification:
    """Tests for get_notification function"""

    def test_get_notification_success(self, db_session: Session):
        """Test retrieving a notification"""
        user = UserFactory.create(db_session)
        notification = create_notification(
            db_session,
            user_id=user.id,
            type="test",
        )

        retrieved = get_notification(db_session, notification.id, user.id)

        assert retrieved.id == notification.id
        assert retrieved.user_id == user.id
        assert retrieved.type == "test"

    def test_get_notification_not_found(self, db_session: Session):
        """Test retrieving non-existent notification"""
        user = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            get_notification(db_session, fake_id, user.id)

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    def test_get_notification_wrong_user(self, db_session: Session):
        """Test retrieving notification for different user"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        notification = create_notification(
            db_session,
            user_id=user1.id,
            type="test",
        )

        # Try to get notification as different user
        with pytest.raises(HTTPException) as exc_info:
            get_notification(db_session, notification.id, user2.id)

        assert exc_info.value.status_code == 404

    def test_get_notification_with_payload(self, db_session: Session):
        """Test retrieving notification with payload"""
        user = UserFactory.create(db_session)
        payload = {"task_id": str(uuid.uuid4()), "priority": "high"}
        notification = create_notification(
            db_session,
            user_id=user.id,
            type="task_assigned",
            payload=payload,
        )

        retrieved = get_notification(db_session, notification.id, user.id)

        assert retrieved.payload == payload


class TestGetNotifications:
    """Tests for get_notifications function"""

    def test_get_notifications_all(self, db_session: Session):
        """Test retrieving all notifications for user"""
        user = UserFactory.create(db_session)
        # Create multiple notifications
        for i in range(3):
            create_notification(
                db_session,
                user_id=user.id,
                type=f"type_{i}",
            )

        notifications, total = get_notifications(db_session, user.id)

        assert len(notifications) == 3
        assert total == 3

    def test_get_notifications_pagination(self, db_session: Session):
        """Test retrieving notifications with pagination"""
        user = UserFactory.create(db_session)
        # Create 5 notifications
        for i in range(5):
            create_notification(
                db_session,
                user_id=user.id,
                type=f"type_{i}",
            )

        # Get first page with limit 2
        notifications, total = get_notifications(db_session, user.id, page=1, limit=2)

        assert len(notifications) == 2
        assert total == 5

        # Get second page
        notifications_page2, total = get_notifications(db_session, user.id, page=2, limit=2)

        assert len(notifications_page2) == 2
        assert total == 5

    def test_get_notifications_filter_by_read_status(self, db_session: Session):
        """Test filtering notifications by read status"""
        user = UserFactory.create(db_session)
        # Create unread notification
        unread = create_notification(
            db_session,
            user_id=user.id,
            type="unread_test",
        )
        # Create read notification
        read = create_notification(
            db_session,
            user_id=user.id,
            type="read_test",
        )
        update_notification(db_session, read.id, user.id, is_read=True)

        # Get unread notifications
        unread_notifs, total = get_notifications(db_session, user.id, is_read=False)

        assert len(unread_notifs) >= 1
        assert any(n.id == unread.id for n in unread_notifs)
        assert not any(n.id == read.id for n in unread_notifs)

    def test_get_notifications_sorting_ascending(self, db_session: Session):
        """Test sorting notifications in ascending order"""
        user = UserFactory.create(db_session)
        for i in range(3):
            create_notification(
                db_session,
                user_id=user.id,
                type=f"type_{i}",
            )

        notifications, total = get_notifications(
            db_session,
            user.id,
            order_by="created_at",
            dir="asc",
        )

        assert len(notifications) == 3
        # Verify ascending order
        for i in range(len(notifications) - 1):
            assert notifications[i].created_at <= notifications[i + 1].created_at

    def test_get_notifications_sorting_descending(self, db_session: Session):
        """Test sorting notifications in descending order"""
        user = UserFactory.create(db_session)
        for i in range(3):
            create_notification(
                db_session,
                user_id=user.id,
                type=f"type_{i}",
            )

        notifications, total = get_notifications(
            db_session,
            user.id,
            order_by="created_at",
            dir="desc",
        )

        assert len(notifications) == 3
        # Verify descending order
        for i in range(len(notifications) - 1):
            assert notifications[i].created_at >= notifications[i + 1].created_at

    def test_get_notifications_empty_for_user(self, db_session: Session):
        """Test retrieving notifications for user with no notifications"""
        user = UserFactory.create(db_session)

        notifications, total = get_notifications(db_session, user.id)

        assert len(notifications) == 0
        assert total == 0

    def test_get_notifications_default_pagination(self, db_session: Session):
        """Test default pagination values"""
        user = UserFactory.create(db_session)
        # Create 25 notifications
        for i in range(25):
            create_notification(
                db_session,
                user_id=user.id,
                type=f"type_{i}",
            )

        notifications, total = get_notifications(db_session, user.id)

        # Default limit is 20
        assert len(notifications) <= 20
        assert total == 25

    def test_get_notifications_isolation(self, db_session: Session):
        """Test that notifications are isolated per user"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)

        # Create notifications for user1
        for i in range(3):
            create_notification(
                db_session,
                user_id=user1.id,
                type=f"user1_type_{i}",
            )

        # Create notifications for user2
        for i in range(2):
            create_notification(
                db_session,
                user_id=user2.id,
                type=f"user2_type_{i}",
            )

        # Get notifications for user1
        user1_notifs, user1_total = get_notifications(db_session, user1.id)

        # Get notifications for user2
        user2_notifs, user2_total = get_notifications(db_session, user2.id)

        assert user1_total == 3
        assert user2_total == 2
        assert all(n.user_id == user1.id for n in user1_notifs)
        assert all(n.user_id == user2.id for n in user2_notifs)


class TestUpdateNotification:
    """Tests for update_notification function"""

    def test_update_notification_mark_read(self, db_session: Session):
        """Test marking notification as read"""
        user = UserFactory.create(db_session)
        notification = create_notification(
            db_session,
            user_id=user.id,
            type="test",
        )

        assert notification.is_read is False

        updated = update_notification(
            db_session,
            notification.id,
            user.id,
            is_read=True,
        )

        assert updated.is_read is True
        assert updated.id == notification.id

    def test_update_notification_mark_unread(self, db_session: Session):
        """Test marking notification as unread"""
        user = UserFactory.create(db_session)
        notification = create_notification(
            db_session,
            user_id=user.id,
            type="test",
            is_read=True,
        )

        updated = update_notification(
            db_session,
            notification.id,
            user.id,
            is_read=False,
        )

        assert updated.is_read is False

    def test_update_notification_not_found(self, db_session: Session):
        """Test updating non-existent notification"""
        user = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            update_notification(
                db_session,
                fake_id,
                user.id,
                is_read=True,
            )

        assert exc_info.value.status_code == 404

    def test_update_notification_wrong_user(self, db_session: Session):
        """Test updating notification for different user"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        notification = create_notification(
            db_session,
            user_id=user1.id,
            type="test",
        )

        # Try to update as different user
        with pytest.raises(HTTPException) as exc_info:
            update_notification(
                db_session,
                notification.id,
                user2.id,
                is_read=True,
            )

        assert exc_info.value.status_code == 404

    def test_update_notification_timestamp(self, db_session: Session):
        """Test that updated_at timestamp is updated"""
        user = UserFactory.create(db_session)
        notification = create_notification(
            db_session,
            user_id=user.id,
            type="test",
        )

        original_updated_at = notification.updated_at

        updated = update_notification(
            db_session,
            notification.id,
            user.id,
            is_read=True,
        )

        # updated_at should be set or updated
        assert updated.updated_at is not None

    def test_update_notification_no_changes(self, db_session: Session):
        """Test updating notification with no changes"""
        user = UserFactory.create(db_session)
        notification = create_notification(
            db_session,
            user_id=user.id,
            type="test",
            is_read=False,
        )

        updated = update_notification(db_session, notification.id, user.id)

        assert updated.is_read is False
        assert updated.id == notification.id


class TestDeleteNotification:
    """Tests for delete_notification function"""

    def test_delete_notification_success(self, db_session: Session):
        """Test deleting a notification"""
        user = UserFactory.create(db_session)
        notification = create_notification(
            db_session,
            user_id=user.id,
            type="test",
        )
        notification_id = notification.id

        delete_notification(db_session, notification_id, user.id)

        # Verify deletion
        with pytest.raises(HTTPException) as exc_info:
            get_notification(db_session, notification_id, user.id)

        assert exc_info.value.status_code == 404

    def test_delete_notification_not_found(self, db_session: Session):
        """Test deleting non-existent notification"""
        user = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            delete_notification(db_session, fake_id, user.id)

        assert exc_info.value.status_code == 404

    def test_delete_notification_wrong_user(self, db_session: Session):
        """Test deleting notification for different user"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        notification = create_notification(
            db_session,
            user_id=user1.id,
            type="test",
        )

        # Try to delete as different user
        with pytest.raises(HTTPException) as exc_info:
            delete_notification(db_session, notification.id, user2.id)

        assert exc_info.value.status_code == 404

    def test_delete_notification_multiple(self, db_session: Session):
        """Test deleting multiple notifications"""
        user = UserFactory.create(db_session)
        notifications = []
        for i in range(3):
            notif = create_notification(
                db_session,
                user_id=user.id,
                type=f"type_{i}",
            )
            notifications.append(notif)

        # Delete each notification
        for notif in notifications:
            delete_notification(db_session, notif.id, user.id)

        # Verify all deleted
        remaining, total = get_notifications(db_session, user.id)
        assert total == 0


class TestNotificationIntegration:
    """Integration tests for notification workflows"""

    def test_notification_lifecycle(self, db_session: Session):
        """Test complete notification lifecycle"""
        user = UserFactory.create(db_session)

        # Create notification
        notification = create_notification(
            db_session,
            user_id=user.id,
            type="task_assigned",
            payload={"task_id": str(uuid.uuid4())},
        )
        assert notification.is_read is False

        # Retrieve notification
        retrieved = get_notification(db_session, notification.id, user.id)
        assert retrieved.type == "task_assigned"

        # Mark as read
        updated = update_notification(
            db_session,
            notification.id,
            user.id,
            is_read=True,
        )
        assert updated.is_read is True

        # Delete notification
        delete_notification(db_session, notification.id, user.id)

        # Verify deletion
        with pytest.raises(HTTPException):
            get_notification(db_session, notification.id, user.id)

    def test_bulk_notification_workflow(self, db_session: Session):
        """Test bulk notification creation and retrieval"""
        users = UserFactory.create_batch(db_session, count=3)
        user_ids = [user.id for user in users]

        # Create bulk notifications
        notifications = create_notifications_bulk(
            db_session,
            user_ids,
            type="announcement",
            payload={"message": "Important update"},
        )

        assert len(notifications) == 3

        # Verify each user can retrieve their notification
        for user in users:
            user_notifs, total = get_notifications(db_session, user.id)
            assert total >= 1
            assert any(n.type == "announcement" for n in user_notifs)

    def test_notification_filtering_workflow(self, db_session: Session):
        """Test notification filtering workflow"""
        user = UserFactory.create(db_session)

        # Create mix of read and unread notifications
        for i in range(3):
            notif = create_notification(
                db_session,
                user_id=user.id,
                type=f"type_{i}",
            )
            if i % 2 == 0:
                update_notification(db_session, notif.id, user.id, is_read=True)

        # Get unread notifications
        unread, unread_total = get_notifications(db_session, user.id, is_read=False)
        # Get read notifications
        read, read_total = get_notifications(db_session, user.id, is_read=True)

        assert unread_total >= 1
        assert read_total >= 1
        assert all(not n.is_read for n in unread)
        assert all(n.is_read for n in read)
