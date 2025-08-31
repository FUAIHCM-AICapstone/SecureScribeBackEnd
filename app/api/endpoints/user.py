import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.common import ApiResponse, PaginatedResponse, create_pagination_meta
from app.services.user import create_user, delete_user, get_users, update_user

router = APIRouter()


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
