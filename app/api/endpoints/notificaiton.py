# Standard library imports
import asyncio
import uuid
from typing import List, Optional
from uuid import UUID

# Third-party imports
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket
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


@router.websocket("/notifications/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(..., description="JWT access token")):
    """
    WebSocket endpoint for real-time task progress updates
    Requires JWT token as query parameter for authentication
    """
    print("=== WEBSOCKET ENDPOINT CALLED ===")
    print(f"Token received: {token[:50]}...")

    try:
        print("Step 1: Verifying token...")
        # Verify token manually
        user_id = get_current_user_from_token(token)
        print(f"Step 2: get_current_user_from_token returned: {user_id}")

        if not user_id:
            print("Step 3: user_id is None/empty - rejecting connection")
            await websocket.close(code=4001, reason="Invalid token")
            return

        print(f"Step 4: Valid user_id obtained: {user_id}")

        # Get user from database
        print("Step 5: Opening database session...")
        db = SessionLocal()
        try:
            print(f"Step 6: Converting user_id to UUID: {UUID(user_id)}")
            user = db.query(User).filter(User.id == UUID(user_id)).first()
            print(f"Step 7: Database query result: {user}")

            if not user:
                print("Step 8: User not found in database - rejecting connection")
                await websocket.close(code=4002, reason="User not found")
                return

            print(f"Step 9: User found successfully: {user.id}")
        finally:
            print("Step 10: Closing database session")
            db.close()

        print("Step 11: Authentication successful, accepting WebSocket connection")

        # Accept the WebSocket connection
        await websocket.accept()
        print("Step 12: WebSocket connection accepted")

        # Import websocket_manager here to avoid circular imports
        from app.services.websocket_manager import websocket_manager

        # Register the connection
        user_id_str = str(user.id)
        websocket_manager.add_connection(user_id_str, websocket)
        print(f"Step 13: WebSocket registered for user: {user_id_str}")

        try:
            # Send initial connection message
            await websocket.send_json({
                "type": "connected",
                "data": {
                    "user_id": user_id_str,
                    "message": "WebSocket connection established"
                }
            })
            print("Step 14: Initial connection message sent")

            # Handle incoming messages and maintain connection
            while True:
                try:
                    # Wait for messages with timeout (heartbeat)
                    data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                    print(f"Received message from {user_id_str}: {data}")

                    # Handle client messages if needed
                    if data.get("type") == "ping":
                        await websocket.send_json({"type": "pong"})
                        print(f"Sent pong to {user_id_str}")

                except asyncio.TimeoutError:
                    # Send ping to keep connection alive
                    try:
                        await websocket.send_json({"type": "ping"})
                        print(f"Sent ping to {user_id_str}")
                    except Exception:
                        print(f"Failed to send ping to {user_id_str}, connection may be dead")
                        break

                except Exception as e:
                    print(f"WebSocket error for {user_id_str}: {e}")
                    break

        except Exception as e:
            print(f"WebSocket connection error for {user_id_str}: {e}")

        finally:
            # Clean up connection
            websocket_manager.remove_connection(user_id_str)
            print(f"Step 15: WebSocket connection cleaned up for user: {user_id_str}")

    except Exception as e:
        print(f"WebSocket authentication error: {type(e).__name__}: {str(e)}")
        try:
            await websocket.close(code=4000, reason=f"Authentication failed: {str(e)}")
        except Exception:
            pass  # Connection might already be closed
