import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User, UserDevice


def crud_get_notification(db: Session, notification_id: uuid.UUID = None, user_id: uuid.UUID = None, is_read: Optional[bool] = None, order_by: str = "created_at", direction: str = "desc", page: int = 1, limit: int = 20):
    if notification_id and user_id:
        return db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()
    if user_id:
        query = db.query(Notification).filter(Notification.user_id == user_id)
        if is_read is not None:
            query = query.filter(Notification.is_read == is_read)
        total = query.count()
        if direction == "asc":
            query = query.order_by(getattr(Notification, order_by).asc())
        else:
            query = query.order_by(getattr(Notification, order_by).desc())
        notifications = query.offset((page - 1) * limit).limit(limit).all()
        return notifications, total
    return None


def crud_create_notification(db: Session, user_id: uuid.UUID, **kwargs) -> Notification:
    notification = Notification(user_id=user_id, **kwargs)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def crud_create_notifications_bulk(db: Session, user_ids: List[uuid.UUID], **kwargs) -> List[Notification]:
    notifications = []
    for user_id in user_ids:
        notification = Notification(user_id=user_id, **kwargs)
        db.add(notification)
        notifications.append(notification)
    db.commit()
    for notification in notifications:
        db.refresh(notification)
    return notifications


def crud_create_global_notification(db: Session, **kwargs) -> List[Notification]:
    users = db.query(User).all()
    user_ids = [user.id for user in users]
    return crud_create_notifications_bulk(db, user_ids, **kwargs)


def crud_update_notification(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID, **kwargs) -> Optional[Notification]:
    notification = crud_get_notification(db, notification_id, user_id)
    if not notification:
        return None
    for key, value in kwargs.items():
        if value is not None:
            setattr(notification, key, value)
    notification.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(notification)
    return notification


def crud_delete_notification(db: Session, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    notification = crud_get_notification(db, notification_id, user_id)
    if not notification:
        return False
    db.delete(notification)
    db.commit()
    return True


def crud_get_user_fcm_tokens(db: Session, user_ids: List[uuid.UUID]) -> List[str]:
    tokens = []
    for user_id in user_ids:
        devices = db.query(UserDevice).filter(UserDevice.user_id == user_id, UserDevice.is_active == True).all()
        user_tokens = [device.fcm_token for device in devices if device.fcm_token and device.fcm_token.strip()]
        tokens.extend(user_tokens)
    return tokens
