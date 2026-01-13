import uuid
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from firebase_admin import messaging
from sqlalchemy.orm import Session

from app.crud.notification import (
    crud_create_global_notification,
    crud_create_notification,
    crud_create_notifications_bulk,
    crud_delete_notification,
    crud_get_notification,
    crud_get_user_fcm_tokens,
    crud_update_notification,
)
from app.models.notification import Notification


def get_notifications(db: Session, user_id: uuid.UUID, **kwargs) -> Tuple[List[Notification], int]:
    return crud_get_notification(
        db,
        user_id=user_id,
        is_read=kwargs.get("is_read"),
        order_by=kwargs.get("order_by", "created_at"),
        direction=kwargs.get("dir", "desc"),
        page=kwargs.get("page", 1),
        limit=kwargs.get("limit", 20),
    )


def get_notification(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification:
    notification = crud_get_notification(db, notification_id=notification_id, user_id=user_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


def create_notification(db: Session, user_id: uuid.UUID, **kwargs) -> Notification:
    return crud_create_notification(db, user_id, **kwargs)


def create_notifications_bulk(db: Session, user_ids: List[uuid.UUID], **kwargs) -> List[Notification]:
    return crud_create_notifications_bulk(db, user_ids, **kwargs)


def create_global_notification(db: Session, **kwargs) -> List[Notification]:
    return crud_create_global_notification(db, **kwargs)


def update_notification(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Notification:
    notification = crud_update_notification(db, notification_id, user_id, **kwargs)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


def delete_notification(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> None:
    if not crud_delete_notification(db, notification_id, user_id):
        raise HTTPException(status_code=404, detail="Notification not found")


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
    from app.db import SessionLocal

    db = SessionLocal()
    try:
        tokens = crud_get_user_fcm_tokens(db, user_ids)
        if not tokens:
            return
        fcm_data = {}
        if data:
            for key, value in data.items():
                fcm_data[str(key)] = str(value)
        notification_kwargs = {"title": title, "body": body}
        if icon:
            notification_kwargs["icon"] = icon
        if badge:
            notification_kwargs["badge"] = badge
        if sound:
            notification_kwargs["sound"] = sound
        webpush_notification = messaging.WebpushNotification(**notification_kwargs)
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
        try:
            messaging.send_each_for_multicast(message)
        except Exception as e:
            print(f"[FCM Notification] Error sending notification: {str(e)}")
            raise
    finally:
        db.close()
