import warnings
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.constants.messages import MessageDescriptions
from app.crud.notification import (
    crud_create_global_notification,
    crud_create_notification,
    crud_create_notifications_bulk,
    crud_delete_notification,
    crud_get_notification,
    crud_update_notification,
)
from app.models.notification import Notification
from app.utils.logging import logger


def get_notifications(db: Session, user_id: int, **kwargs) -> Tuple[List[Notification], int]:
    return crud_get_notification(
        db,
        user_id=user_id,
        is_read=kwargs.get("is_read"),
        order_by=kwargs.get("order_by", "created_at"),
        direction=kwargs.get("dir", "desc"),
        page=kwargs.get("page", 1),
        limit=kwargs.get("limit", 20),
    )


def get_notification(db: Session, notification_id: int, user_id: int) -> Notification:
    notification = crud_get_notification(db, notification_id=notification_id, user_id=user_id)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageDescriptions.NOTIFICATION_NOT_FOUND)
    return notification


def create_notification(db: Session, user_id: int, **kwargs) -> Notification:
    return crud_create_notification(db, user_id, **kwargs)


def create_notifications_bulk(db: Session, user_ids: List[int], **kwargs) -> List[Notification]:
    return crud_create_notifications_bulk(db, user_ids, **kwargs)


def create_global_notification(db: Session, **kwargs) -> List[Notification]:
    return crud_create_global_notification(db, **kwargs)


def update_notification(db: Session, notification_id: int, user_id: int, **kwargs) -> Notification:
    notification = crud_update_notification(db, notification_id, user_id, **kwargs)
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageDescriptions.NOTIFICATION_NOT_FOUND)
    return notification


def delete_notification(db: Session, notification_id: int, user_id: int) -> None:
    if not crud_delete_notification(db, notification_id, user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageDescriptions.NOTIFICATION_NOT_FOUND)


def send_fcm_notification(
    user_ids: List[int],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    icon: Optional[str] = None,
    badge: Optional[str] = None,
    sound: Optional[str] = None,
    ttl: Optional[int] = None,
) -> None:
    """
    DEPRECATED: Firebase Cloud Messaging is no longer available.
    This function is deprecated and will not send any notifications.

    Firebase has been replaced with Azure AD OAuth for authentication.
    For push notifications, please implement an alternative solution
    using your preferred push notification service.

    Args:
        user_ids: List of user IDs to send notification to
        title: Notification title
        body: Notification body
        data: Optional notification data
        icon: Optional notification icon
        badge: Optional notification badge
        sound: Optional notification sound
        ttl: Optional time-to-live in seconds
    """
    warnings.warn("send_fcm_notification is deprecated and will not send any notifications. Firebase Cloud Messaging is no longer available. Please implement an alternative push notification solution.", DeprecationWarning, stacklevel=2)
    logger.warning(f"send_fcm_notification called but Firebase is no longer available. Attempted to send notification to {len(user_ids)} user(s): {title}")
    return None
