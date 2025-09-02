import uuid
from datetime import datetime
from typing import List, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.user import User


def get_users(db: Session, **kwargs) -> Tuple[List[User], int]:
    query = db.query(User).options(
        selectinload(User.identities),
        selectinload(User.devices),
        selectinload(User.projects),
        selectinload(User.created_projects),
        selectinload(User.created_meetings),
        selectinload(User.uploaded_files),
        selectinload(User.uploaded_audio_files),
        selectinload(User.created_tags),
        selectinload(User.created_tasks),
        selectinload(User.assigned_tasks),
        selectinload(User.notifications),
        selectinload(User.audit_logs),
        selectinload(User.edited_notes),
        selectinload(User.created_bots),
    )

    # Apply filters
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

    # Get total count before pagination
    total = query.count()

    # Apply ordering
    order_by = kwargs.get("order_by", "created_at")
    dir = kwargs.get("dir", "desc")
    if dir == "asc":
        query = query.order_by(getattr(User, order_by).asc())
    else:
        query = query.order_by(getattr(User, order_by).desc())

    # Apply pagination
    page = int(kwargs.get("page", 1))
    limit = int(kwargs.get("limit", 20))
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    users = query.all()
    return users, total


def check_email_exists(db: Session, email: str) -> bool:
    try:
        user = db.query(User).filter(User.email == email).first()
        return user is not None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error while checking email: {str(e)}",
        )


def update_user(db: Session, user_id: uuid.UUID, **updates) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    for key, value in updates.items():
        if hasattr(user, key):
            setattr(user, key, value)
    try:
        db.commit()
        db.refresh(user)
        db.refresh(
            user,
            [
                "identities",
                "devices",
                "projects",
                "created_projects",
                "created_meetings",
                "uploaded_files",
                "uploaded_audio_files",
                "created_tags",
                "created_tasks",
                "assigned_tasks",
                "notifications",
                "audit_logs",
                "edited_notes",
                "created_bots",
            ],
        )
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User update failed: {str(e)}",
        )


def create_user(db: Session, **user_data) -> User:
    user = User(**user_data)
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User creation failed: {str(e)}",
        )


def delete_user(db: Session, user_id: uuid.UUID) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    try:
        db.delete(user)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User deletion failed: {str(e)}",
        )


def bulk_create_users(db: Session, users_data: List[dict]) -> List[dict]:
    """Bulk create users and return results with success/failure status"""
    results = []
    created_users = []

    for user_data in users_data:
        try:
            user = User(**user_data)
            db.add(user)
            db.flush()  # Get the ID without committing
            results.append({"success": True, "id": user.id, "error": None})
            created_users.append(user)
        except Exception as e:
            results.append({"success": False, "id": None, "error": str(e)})

    try:
        db.commit()
        # Refresh all created users
        for user in created_users:
            db.refresh(user)
    except Exception as e:
        db.rollback()
        # Mark all as failed if commit fails
        for result in results:
            if result["success"]:
                result["success"] = False
                result["error"] = f"Commit failed: {str(e)}"
                result["id"] = None

    return results


def bulk_update_users(db: Session, updates: List[dict]) -> List[dict]:
    """Bulk update users and return results with success/failure status"""
    results = []

    for update_item in updates:
        user_id = update_item["id"]
        update_data = update_item["updates"]

        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                results.append(
                    {"success": False, "id": user_id, "error": "User not found"}
                )
                continue

            for key, value in update_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            results.append({"success": True, "id": user_id, "error": None})
        except Exception as e:
            results.append({"success": False, "id": user_id, "error": str(e)})

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # Mark all as failed if commit fails
        for result in results:
            if result["success"]:
                result["success"] = False
                result["error"] = f"Commit failed: {str(e)}"

    return results


def bulk_delete_users(db: Session, user_ids: List[uuid.UUID]) -> List[dict]:
    """Bulk delete users and return results with success/failure status"""
    results = []

    for user_id in user_ids:
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                results.append(
                    {"success": False, "id": user_id, "error": "User not found"}
                )
                continue

            db.delete(user)
            results.append({"success": True, "id": user_id, "error": None})
        except Exception as e:
            results.append({"success": False, "id": user_id, "error": str(e)})

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        # Mark all as failed if commit fails
        for result in results:
            if result["success"]:
                result["success"] = False
                result["error"] = f"Commit failed: {str(e)}"

    return results
