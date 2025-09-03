import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User, UserDevice
from app.schemas.common import ApiResponse, PaginatedResponse, create_pagination_meta
from app.schemas.user import (
    BulkUserCreate,
    BulkUserResponse,
    BulkUserUpdate,
    DeviceFCMUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.user import (
    bulk_create_users,
    bulk_delete_users,
    bulk_update_users,
    create_user,
    delete_user,
    get_users,
    update_user,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["User"])


@router.get("/users", response_model=PaginatedResponse[UserResponse])
def get_users_endpoint(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    order_by: str = Query("created_at"),
    dir: str = Query("desc"),
    name: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    position: Optional[str] = Query(None),
    created_at_gte: Optional[str] = Query(None),
    created_at_lte: Optional[str] = Query(None),
):
    kwargs = {
        "page": page,
        "limit": limit,
        "order_by": order_by,
        "dir": dir,
        "name": name,
        "email": email,
        "position": position,
        "created_at_gte": created_at_gte,
        "created_at_lte": created_at_lte,
    }
    users, total = get_users(db, **kwargs)

    pagination_meta = create_pagination_meta(page, limit, total)

    return PaginatedResponse(
        success=True,
        message="Users retrieved successfully",
        data=users,
        pagination=pagination_meta,
    )


@router.post("/users", response_model=ApiResponse[UserResponse])
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    created_user = create_user(db, **user.model_dump())
    return ApiResponse(
        success=True, message="User created successfully", data=created_user
    )


@router.post("/users/bulk", response_model=BulkUserResponse)
def bulk_create_users_endpoint(
    bulk_request: BulkUserCreate, db: Session = Depends(get_db)
):
    users_data = [user.model_dump() for user in bulk_request.users]
    results = bulk_create_users(db, users_data)

    total_processed = len(results)
    total_success = sum(1 for r in results if r["success"])
    total_failed = total_processed - total_success

    return BulkUserResponse(
        success=total_failed == 0,
        message=f"Bulk user creation completed. {total_success} successful, {total_failed} failed.",
        data=results,
        total_processed=total_processed,
        total_success=total_success,
        total_failed=total_failed,
    )


@router.put("/users/bulk", response_model=BulkUserResponse)
def bulk_update_users_endpoint(
    bulk_request: BulkUserUpdate, db: Session = Depends(get_db)
):
    updates = [
        {"id": item.id, "updates": item.updates.model_dump(exclude_unset=True)}
        for item in bulk_request.users
    ]
    results = bulk_update_users(db, updates)

    total_processed = len(results)
    total_success = sum(1 for r in results if r["success"])
    total_failed = total_processed - total_success

    return BulkUserResponse(
        success=total_failed == 0,
        message=f"Bulk user update completed. {total_success} successful, {total_failed} failed.",
        data=results,
        total_processed=total_processed,
        total_success=total_success,
        total_failed=total_failed,
    )


@router.delete("/users/bulk", response_model=BulkUserResponse)
def bulk_delete_users_endpoint(
    user_ids: str = Query(
        ..., description="Comma-separated list of user IDs to delete"
    ),
    db: Session = Depends(get_db),
):
    # Parse comma-separated user IDs
    try:
        user_id_list = [
            uuid.UUID(uid.strip()) for uid in user_ids.split(",") if uid.strip()
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid UUID format: {e}")

    results = bulk_delete_users(db, user_id_list)

    total_processed = len(results)
    total_success = sum(1 for r in results if r["success"])
    total_failed = total_processed - total_success

    return BulkUserResponse(
        success=total_failed == 0,
        message=f"Bulk user deletion completed. {total_success} successful, {total_failed} failed.",
        data=results,
        total_processed=total_processed,
        total_success=total_success,
        total_failed=total_failed,
    )


@router.put("/users/{user_id}", response_model=ApiResponse[UserResponse])
def update_user_endpoint(
    user_id: uuid.UUID, user: UserUpdate, db: Session = Depends(get_db)
):
    updated_user = update_user(
        db, user_id=user_id, **user.model_dump(exclude_unset=True)
    )
    return ApiResponse(
        success=True, message="User updated successfully", data=updated_user
    )


@router.delete("/users/{user_id}", response_model=ApiResponse[dict])
def delete_user_endpoint(user_id: uuid.UUID, db: Session = Depends(get_db)):
    delete_user(db, user_id=user_id)
    return ApiResponse(success=True, message="User deleted successfully", data={})


@router.post("/users/me/devices/fcm-token", response_model=ApiResponse[dict])
def update_fcm_token_endpoint(
    fcm_data: DeviceFCMUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    # Find existing device or create new one
    device = (
        db.query(UserDevice)
        .filter(
            UserDevice.user_id == current_user.id,
            UserDevice.device_name == fcm_data.device_name,
        )
        .first()
    )

    if device:
        device.fcm_token = fcm_data.fcm_token
        device.device_type = fcm_data.device_type
        device.last_active_at = datetime.utcnow()
        device.is_active = True
    else:
        device = UserDevice(
            user_id=current_user.id,
            device_name=fcm_data.device_name,
            device_type=fcm_data.device_type,
            fcm_token=fcm_data.fcm_token,
            is_active=True,
        )
        db.add(device)

    try:
        db.commit()
        db.refresh(device)
    except Exception:
        db.rollback()
        raise

    return ApiResponse(
        success=True,
        message="FCM token updated successfully",
        data={"device_id": device.id},
    )


@router.post("/users/me/test-stream", response_model=ApiResponse[dict])
def test_stream_progress(current_user: User = Depends(get_current_user)):
    from app.jobs.celery_worker import send_test_notification_task

    user_id_str = str(current_user.id)
    task = send_test_notification_task.delay(user_id_str)

    return ApiResponse(
        success=True,
        message="Stream test started",
        data={
            "task_id": task.id,
            "user_id": user_id_str,
            "status": "started"
        },
    )


@router.get("/users/me/websocket-status", response_model=ApiResponse[dict])
def get_websocket_status(current_user: User = Depends(get_current_user)):
    """
    Get WebSocket connection status for current user
    """
    from app.services.websocket_manager import websocket_manager

    user_id_str = str(current_user.id)

    stats = websocket_manager.get_connection_stats()

    return ApiResponse(
        success=True,
        message="WebSocket status retrieved",
        data={
            "user_id": user_id_str,
            "is_connected": user_id_str in websocket_manager.connections,
            "user_connections": stats.get("connections_per_user", {}).get(user_id_str, 0),
            "total_active_connections": stats.get("active_connections", 0),
            "total_unique_users": stats.get("unique_users", 0),
            "metrics": {
                "total_connections_ever": stats.get("total_connections", 0),
                "messages_sent": stats.get("messages_sent", 0),
                "messages_received": stats.get("messages_received", 0),
                "redis_errors": stats.get("redis_errors", 0),
                "websocket_errors": stats.get("websocket_errors", 0),
            }
        },
    )


@router.get("/admin/metrics/websocket", response_model=ApiResponse[dict])
def get_websocket_metrics(current_user: User = Depends(get_current_user)):
    """
    Get comprehensive WebSocket and Redis metrics (admin endpoint)
    """
    from app.services.websocket_manager import websocket_manager

    # Check if user has admin privileges (you can customize this logic)
    # For now, allowing all authenticated users to view metrics

    stats = websocket_manager.get_connection_stats()

    return ApiResponse(
        success=True,
        message="WebSocket metrics retrieved",
        data={
            "websocket_manager": {
                "status": "running" if websocket_manager._pubsub_task and not websocket_manager._pubsub_task.done() else "stopped",
                "pubsub_active": websocket_manager._pubsub_task is not None and not websocket_manager._pubsub_task.done(),
            },
            "connections": {
                "total_active": stats.get("active_connections", 0),
                "unique_users": stats.get("unique_users", 0),
                "total_ever_connected": stats.get("total_connections", 0),
                "connections_per_user": stats.get("connections_per_user", {}),
            },
            "messages": {
                "total_sent": stats.get("messages_sent", 0),
                "total_received": stats.get("messages_received", 0),
            },
            "errors": {
                "redis_errors": stats.get("redis_errors", 0),
                "websocket_errors": stats.get("websocket_errors", 0),
            },
            "performance": {
                "avg_messages_per_connection": (
                    stats.get("messages_sent", 0) / max(stats.get("active_connections", 1), 1)
                ),
                "error_rate_percent": (
                    (stats.get("redis_errors", 0) + stats.get("websocket_errors", 0)) /
                    max(stats.get("messages_sent", 1), 1) * 100
                ),
            }
        },
    )

