import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.schemas.common import ApiResponse, PaginatedResponse, create_pagination_meta
from app.schemas.user import (
    BulkUserCreate,
    BulkUserResponse,
    BulkUserUpdate,
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
