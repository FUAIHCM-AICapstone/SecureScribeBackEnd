import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.constants.messages import MessageDescriptions
from app.crud.user import crud_check_email_exists, crud_create_user, crud_delete_user_with_cascade, crud_get_or_create_user_device, crud_get_user_by_id, crud_get_users, crud_update_user
from app.events.domain_events import BaseDomainEvent, build_diff
from app.models.project import UserProject
from app.models.user import User
from app.services.event_manager import EventManager


def get_users(db: Session, **kwargs) -> Tuple[List[User], int]:
    return crud_get_users(db, **kwargs)


def check_email_exists(db: Session, email: str) -> bool:
    try:
        return crud_check_email_exists(db, email)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MessageDescriptions.INTERNAL_SERVER_ERROR,
        )


def update_user(db: Session, user_id: uuid.UUID, actor_user_id: uuid.UUID | None = None, **updates) -> User:
    user = crud_get_user_by_id(db, user_id)
    if not user:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="user.update_failed",
                actor_user_id=actor_user_id or user_id,
                target_type="user",
                target_id=user_id,
                metadata={"reason": "not_found"},
            )
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageDescriptions.USER_NOT_FOUND)
    original = {k: getattr(user, k, None) for k in updates.keys() if hasattr(user, k)}
    user = crud_update_user(db, user_id, **updates)
    diff = build_diff(original, {k: getattr(user, k, None) for k in original.keys()})
    if diff:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="user.updated",
                actor_user_id=actor_user_id or user_id,
                target_type="user",
                target_id=user.id,
                metadata={"diff": diff},
            )
        )
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


def create_user(db: Session, actor_user_id: uuid.UUID | None = None, **user_data) -> User:
    email = user_data.get("email")
    if email and crud_check_email_exists(db, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=MessageDescriptions.RESOURCE_ALREADY_EXISTS,
        )
    user = crud_create_user(db, **user_data)
    EventManager.emit_domain_event(
        BaseDomainEvent(
            event_name="user.created",
            actor_user_id=actor_user_id or user.id,
            target_type="user",
            target_id=user.id,
            metadata={"email": user.email},
        )
    )
    return user


def delete_user(db: Session, user_id: uuid.UUID, actor_user_id: uuid.UUID | None = None) -> bool:
    user = crud_get_user_by_id(db, user_id)
    if not user:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="user.delete_failed",
                actor_user_id=actor_user_id or user_id,
                target_type="user",
                target_id=user_id,
                metadata={"reason": "not_found"},
            )
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageDescriptions.USER_NOT_FOUND)

    try:
        # Soft delete user's meetings
        from app.models.meeting import Meeting

        db.query(Meeting).filter(Meeting.created_by == user_id, Meeting.is_deleted == False).update({"is_deleted": True})

        result = crud_delete_user_with_cascade(db, user_id)
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="user.deleted",
                actor_user_id=actor_user_id or user_id,
                target_type="user",
                target_id=user_id,
                metadata={},
            )
        )
        return result
    except Exception as e:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="user.delete_failed",
                actor_user_id=actor_user_id or user_id,
                target_type="user",
                target_id=user_id,
                metadata={"reason": "exception", "detail": str(e)},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=MessageDescriptions.INTERNAL_SERVER_ERROR,
        )


def bulk_create_users(db: Session, users_data: List[dict]) -> List[dict]:
    results = []
    for user_data in users_data:
        try:
            user = create_user(db, **user_data)
            results.append({"success": True, "id": user.id, "error": None})
        except Exception as e:
            results.append({"success": False, "id": None, "error": str(e)})
    return results


def bulk_update_users(db: Session, updates: List[dict]) -> List[dict]:
    results = []
    for update_item in updates:
        user_id = update_item["id"]
        update_data = update_item["updates"]
        try:
            user = update_user(db, user_id, **update_data)
            results.append({"success": True, "id": user_id, "error": None})
        except Exception as e:
            results.append({"success": False, "id": user_id, "error": str(e)})
    return results


def bulk_delete_users(db: Session, user_ids: List[uuid.UUID]) -> List[dict]:
    results = []
    for user_id in user_ids:
        try:
            success = delete_user(db, user_id)
            if success:
                results.append({"success": True, "id": user_id, "error": None})
            else:
                results.append({"success": False, "id": user_id, "error": MessageDescriptions.USER_NOT_FOUND})
        except Exception as e:
            results.append({"success": False, "id": user_id, "error": str(e)})
    return results


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return crud_get_user_by_id(db, user_id)


def get_user_projects_stats(db: Session, user_id: uuid.UUID) -> dict:
    """Get user's project statistics"""

    # Get user's projects directly
    user_projects = db.query(UserProject).options(selectinload(UserProject.project)).filter(UserProject.user_id == user_id).all()

    # Calculate statistics
    total_projects = len(user_projects)
    admin_projects = sum(1 for up in user_projects if up.role in ["admin", "owner"])
    member_projects = total_projects - admin_projects
    active_projects = sum(1 for up in user_projects if up.project and not up.project.is_archived)

    return {
        "total_projects": total_projects,
        "admin_projects": admin_projects,
        "member_projects": member_projects,
        "active_projects": active_projects,
        "archived_projects": total_projects - active_projects,
    }


def get_or_create_user_device(db: Session, user_id: uuid.UUID, device_name: str, device_type: str, fcm_token: str):
    return crud_get_or_create_user_device(db, user_id, device_name, device_type, fcm_token)
