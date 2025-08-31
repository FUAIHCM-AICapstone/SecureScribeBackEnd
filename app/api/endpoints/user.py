from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.user import UserResponse
from app.services.user import get_users

router = APIRouter()


@router.get("/users", response_model=List[UserResponse])
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
    users = get_users(db, **kwargs)
    return users
