from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.models.user import User


def get_users(db: Session, **kwargs) -> List[User]:
    query = db.query(User)

    if "name" in kwargs and kwargs["name"]:
        query = query.filter(User.name.ilike(f"%{kwargs['name']}%"))
    if "email" in kwargs and kwargs["email"]:
        query = query.filter(User.email == kwargs["email"])
    if "position" in kwargs and kwargs["position"]:
        query = query.filter(User.position == kwargs["position"])
    if "created_at_gte" in kwargs and kwargs["created_at_gte"]:
        gte = datetime.fromisoformat(kwargs["created_at_gte"])
        query = query.filter(User.created_at >= gte)
    if "created_at_lte" in kwargs and kwargs["created_at_lte"]:
        lte = datetime.fromisoformat(kwargs["created_at_lte"])
        query = query.filter(User.created_at <= lte)

    order_by = kwargs.get("order_by", "created_at")
    dir = kwargs.get("dir", "desc")
    if dir == "asc":
        query = query.order_by(getattr(User, order_by).asc())
    else:
        query = query.order_by(getattr(User, order_by).desc())

    page = int(kwargs.get("page", 1))
    limit = int(kwargs.get("limit", 20))
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    return query.all()
