import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, create_pagination_meta
from app.schemas.notification import (
    NotificationCreate,
    NotificationGlobalCreate,
    NotificationResponse,
    NotificationUpdate,
)
from app.services.notification import (
    create_global_notification,
    create_notifications_bulk,
    delete_notification,
    get_notification,
    get_notifications,
    send_fcm_notification,
    update_notification,
)
from app.utils.auth import get_current_user

from ...models.user import User

router = APIRouter(prefix=settings.API_V1_STR, tags=["Notification"])


@router.get("/notifications", response_model=PaginatedResponse[NotificationResponse])
def get_notifications_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    order_by: str = Query("created_at"),
    dir: str = Query("desc"),
    is_read: Optional[bool] = Query(None),
):
    kwargs = {
        "page": page,
        "limit": limit,
        "order_by": order_by,
        "dir": dir,
        "is_read": is_read,
    }
    notifications, total = get_notifications(db, current_user.id, **kwargs)

    pagination_meta = create_pagination_meta(page, limit, total)

    return PaginatedResponse(
        success=True,
        message="Notifications retrieved successfully",
        data=notifications,
        pagination=pagination_meta,
    )


@router.get(
    "/notifications/{notification_id}", response_model=ApiResponse[NotificationResponse]
)
def get_notification_endpoint(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = get_notification(db, notification_id, current_user.id)
    return ApiResponse(
        success=True,
        message="Notification retrieved successfully",
        data=notification,
    )


@router.post(
    "/notifications/send", response_model=ApiResponse[List[NotificationResponse]]
)
def send_notification_endpoint(
    notification_data: NotificationCreate,
    db: Session = Depends(get_db),
):
    notifications = create_notifications_bulk(
        db,
        notification_data.user_ids,
        type=notification_data.type,
        payload=notification_data.payload,
        channel=notification_data.channel,
    )
    if notification_data.payload:
        title = notification_data.payload.get("title", "Notification")
        body = notification_data.payload.get("body", "")
        send_fcm_notification(
            notification_data.user_ids, title, body, notification_data.payload
        )
    return ApiResponse(
        success=True,
        message="Notifications sent successfully",
        data=notifications,
    )


@router.post(
    "/notifications/send-global", response_model=ApiResponse[List[NotificationResponse]]
)
def send_global_notification_endpoint(
    notification_data: NotificationGlobalCreate,
    db: Session = Depends(get_db),
):
    notifications = create_global_notification(
        db,
        type=notification_data.type,
        payload=notification_data.payload,
        channel=notification_data.channel,
    )

    user_ids = [n.user_id for n in notifications]

    if notification_data.payload:
        title = notification_data.payload.get("title", "Global Notification")
        body = notification_data.payload.get("body", "")
        send_fcm_notification(user_ids, title, body, notification_data.payload)

    return ApiResponse(
        success=True,
        message="Global notifications sent successfully",
        data=notifications,
    )


@router.patch(
    "/notifications/{notification_id}/read",
    response_model=ApiResponse[NotificationResponse],
)
def mark_notification_read_endpoint(
    notification_id: uuid.UUID,
    update_data: NotificationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = update_notification(
        db,
        notification_id,
        current_user.id,
        is_read=update_data.is_read,
    )
    return ApiResponse(
        success=True,
        message="Notification updated successfully",
        data=notification,
    )


@router.delete("/notifications/{notification_id}", response_model=ApiResponse[None])
def delete_notification_endpoint(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_notification(db, notification_id, current_user.id)
    return ApiResponse(
        success=True,
        message="Notification deleted successfully",
        data=None,
    )


@router.get("/notifications/stream")
def stream_notifications():
    def event_generator():
        yield 'data: {"type": "connected", "message": "Notification stream connected"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
