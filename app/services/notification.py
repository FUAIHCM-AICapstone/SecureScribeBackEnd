import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from firebase_admin import messaging
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User, UserDevice


def get_notifications(db: Session, user_id: uuid.UUID, **kwargs) -> Tuple[List[Notification], int]:
    query = db.query(Notification).filter(Notification.user_id == user_id)

    if "is_read" in kwargs and kwargs["is_read"] is not None:
        query = query.filter(Notification.is_read == kwargs["is_read"])

    total = query.count()

    page = kwargs.get("page", 1)
    limit = kwargs.get("limit", 20)
    offset = (page - 1) * limit

    order_by = kwargs.get("order_by", "created_at")
    dir = kwargs.get("dir", "desc")

    if dir == "asc":
        query = query.order_by(getattr(Notification, order_by).asc())
    else:
        query = query.order_by(getattr(Notification, order_by).desc())

    notifications = query.offset(offset).limit(limit).all()
    return notifications, total


def get_notification(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
    notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


def create_notification(db: Session, user_id: uuid.UUID, **kwargs) -> Notification:
    notification = Notification(user_id=user_id, **kwargs)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def create_notifications_bulk(db: Session, user_ids: List[uuid.UUID], **kwargs) -> List[Notification]:
    notifications = []
    for user_id in user_ids:
        print(f"[create_notifications_bulk] Creating notification for user: {user_id}")
        notification = Notification(user_id=user_id, **kwargs)
        db.add(notification)
        notifications.append(notification)
    print(f"[create_notifications_bulk] Committing {len(notifications)} notifications to the database")
    db.commit()
    for notification in notifications:
        db.refresh(notification)
    return notifications


def create_global_notification(db: Session, **kwargs) -> List[Notification]:
    users = db.query(User).all()
    user_ids = [user.id for user in users]
    return create_notifications_bulk(db, user_ids, **kwargs)


def update_notification(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Notification:
    notification = get_notification(db, notification_id, user_id)
    for key, value in kwargs.items():
        if value is not None:
            setattr(notification, key, value)
    notification.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification


def delete_notification(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> None:
    notification = get_notification(db, notification_id, user_id)
    db.delete(notification)
    db.commit()


def send_fcm_notification(
    user_ids: List[uuid.UUID],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    sound: Optional[str] = None,
    ttl: Optional[int] = None,
) -> None:
    print(f"[FCM] Starting FCM notification send to {len(user_ids)} users. Title: '{title}'")
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        tokens = []
        for user_id in user_ids:
            devices: List[UserDevice] = db.query(UserDevice).filter(UserDevice.user_id == user_id, UserDevice.is_active == True).all()
            user_tokens = [device.fcm_token for device in devices if device.fcm_token and device.fcm_token.strip()]
            tokens.extend(user_tokens)
            print(f"[FCM] User {user_id}: Found {len(user_tokens)} active FCM tokens")

        print(f"[FCM] Total FCM tokens collected: {len(tokens)}")
        if not tokens:
            print("[FCM] No active FCM tokens found, skipping notification send")
            return

        # Ensure all data values are strings as required by FCM
        fcm_data = {}
        if data:
            for key, value in data.items():
                fcm_data[str(key)] = str(value)
            print(f"[FCM] Prepared FCM data payload with {len(fcm_data)} fields")

        # Build webpush notification
        notification_kwargs = {"title": title, "body": body}

        if icon:
            notification_kwargs["icon"] = icon

        if badge:
            notification_kwargs["badge"] = badge

        if sound:
            notification_kwargs["sound"] = sound

        webpush_notification = messaging.WebpushNotification(**notification_kwargs)

        # Build webpush config
        webpush_kwargs = {"notification": webpush_notification}

        if ttl:
            headers = {}
            headers["TTL"] = str(ttl)

            webpush_kwargs["headers"] = headers

        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            data=fcm_data,
            tokens=tokens,
        )
        print(f"[FCM] Prepared multicast message for {len(tokens)} tokens")

        try:
            print("[FCM] Sending FCM notification...")
            response = messaging.send_each_for_multicast(message)
            success_count = sum(1 for resp in response.responses if not resp.exception)
            failure_count = sum(1 for resp in response.responses if resp.exception)

            print(f"[FCM] Notification send completed. Success: {success_count}, Failures: {failure_count}")

            for i, resp in enumerate(response.responses):
                if resp.exception:
                    print(f"[FCM] Device {i} failed: {resp.exception}")

            if success_count > 0:
                print("[FCM] FCM notification sent successfully to at least one device")
        except Exception as e:
            print(f"[FCM] Failed to send FCM notification: {str(e)}")
            raise
    finally:
        db.close()
        print("[FCM] FCM notification task completed")
