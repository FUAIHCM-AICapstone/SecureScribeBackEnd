# Standard library imports
import asyncio
import uuid
from typing import List, Optional
from uuid import UUID

# Third-party imports
from fastapi import APIRouter, Depends, Query, WebSocket
from sqlalchemy.orm import Session

# Local imports
from app.core.config import settings
from app.db import SessionLocal, get_db
from app.models.user import User
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
from app.utils.auth import get_current_user, get_current_user_from_token

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

    # Publish to Redis channels for real-time WebSocket delivery
    import asyncio

    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )

    from app.utils.redis import publish_to_user_channel

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        retry=retry_if_exception_type(Exception),
    )
    async def publish_notifications():
        """Publish notifications to Redis with retry logic"""
        for user_id in notification_data.user_ids:
            message = {
                "type": "notification",
                "data": {
                    "notification_type": notification_data.type,
                    "payload": notification_data.payload,
                    "channel": notification_data.channel,
                    "timestamp": asyncio.get_event_loop().time(),
                },
            }
            success = await publish_to_user_channel(str(user_id), message)
            if not success:
                print(f"Failed to publish notification to user {user_id} after retries")

    # Run async publishing in background with error handling
    try:
        asyncio.create_task(publish_notifications())
    except Exception as e:
        print(f"Failed to start notification publishing task: {e}")
        # Continue with FCM even if Redis publishing fails

    # Send FCM notifications
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

    # Publish to Redis channels for real-time WebSocket delivery
    import asyncio

    from tenacity import (
        retry,
        retry_if_exception_type,
        stop_after_attempt,
        wait_exponential,
    )

    from app.utils.redis import publish_to_user_channel

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        retry=retry_if_exception_type(Exception),
    )
    async def publish_global_notifications():
        """Publish global notifications to Redis with retry logic"""
        success_count = 0
        for user_id in user_ids:
            message = {
                "type": "notification",
                "data": {
                    "notification_type": notification_data.type,
                    "payload": notification_data.payload,
                    "channel": notification_data.channel,
                    "is_global": True,
                    "timestamp": asyncio.get_event_loop().time(),
                },
            }
            success = await publish_to_user_channel(str(user_id), message)
            if success:
                success_count += 1
            else:
                print(
                    f"Failed to publish global notification to user {user_id} after retries"
                )

        print(
            f"Published global notifications to {success_count}/{len(user_ids)} users"
        )

    # Run async publishing in background with error handling
    try:
        asyncio.create_task(publish_global_notifications())
    except Exception as e:
        print(f"Failed to start global notification publishing task: {e}")
        # Continue with FCM even if Redis publishing fails

    # Send FCM notifications
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


@router.websocket("/notifications/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    authorization: str = Query(
        None, description="Bearer token in format: Bearer <token>"
    ),
    token: str = Query(None, description="JWT token (legacy support)"),
    sec_websocket_protocol: str = Query(
        None, description="WebSocket subprotocols", alias="sec-websocket-protocol"
    ),
):
    """
    WebSocket endpoint for real-time notifications and task progress updates.

    Supports JWT token authentication via query parameters.

    Query Parameters:
    - authorization: Bearer token (format: "Bearer <jwt_token>") - RECOMMENDED
    - token: JWT token (legacy support)
    """
    user_id = None
    user_id_str = None

    # Import WebSocket manager outside try block
    from app.services.websocket_manager import websocket_manager

    try:
        # Get token from either authorization or token parameter
        auth_token = None
        if authorization and authorization.lower().startswith("bearer "):
            auth_token = authorization[len("bearer ") :].strip()
        elif authorization:
            auth_token = authorization.strip()
        elif token:
            auth_token = token.strip()

        if not auth_token:
            await websocket.close(code=4001, reason="Missing token")
            return

        # Authenticate user
        user_id = get_current_user_from_token(auth_token)
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return

        # Validate user exists
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == UUID(user_id)).first()
            if not user:
                await websocket.close(code=4002, reason="User not found")
                return
        finally:
            db.close()

        user_id_str = str(user.id)
        print(f"WebSocket connected for user: {user_id_str}")

        # Accept WebSocket connection
        await websocket.accept()

        # Add connection to manager
        websocket_manager.add_connection(user_id_str, websocket)

        # Start Redis listener if not already started
        if (
            websocket_manager._pubsub_task is None
            or websocket_manager._pubsub_task.done()
        ):
            asyncio.create_task(websocket_manager.start_redis_listener())

        # Send simple connection confirmation
        connection_message = {
            "type": "connected",
            "data": {
                "user_id": user_id_str,
                "message": "WebSocket connection established",
            },
        }
        await websocket.send_json(connection_message)

        # Send capabilities info
        capabilities_message = {
            "type": "capabilities",
            "data": {
                "supported_message_types": ["task_progress", "notification", "system"]
            },
        }
        await websocket.send_json(capabilities_message)

        # Main message loop
        while True:
            try:
                # Wait for message with timeout
                message = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)

                # Handle client messages
                message_type = message.get("type", "")

                if message_type == "ping":
                    # Respond to ping
                    await websocket.send_json({"type": "pong"})
                    print(f"Ping received from user {user_id_str}")

                elif message_type == "status":
                    # Send simple status
                    await websocket.send_json(
                        {
                            "type": "status",
                            "data": {"user_id": user_id_str, "connected": True},
                        }
                    )

                else:
                    print(f"Message from user {user_id_str}: {message_type}")

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    print(f"Failed to send ping to user {user_id_str}")
                    break

            except Exception as e:
                print(f"WebSocket error for user {user_id_str}: {e}")
                break

    except Exception as e:
        print(f"WebSocket error: {str(e)}")
        try:
            await websocket.close(code=4000, reason="Connection error")
        except Exception:
            pass

    finally:
        # Clean up connection
        if user_id_str and "websocket_manager" in locals():
            try:
                websocket_manager.remove_connection(user_id_str, websocket)
            except Exception:
                pass

        try:
            await websocket.close()
        except Exception:
            pass
