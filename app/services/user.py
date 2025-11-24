import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.events.domain_events import BaseDomainEvent, build_diff
from app.models.file import File
from app.models.meeting import Meeting, ProjectMeeting
from app.models.project import Project, UserProject
from app.models.task import Task, TaskProject
from app.models.user import User
from app.services.event_manager import EventManager
from app.utils.minio import delete_file_from_minio


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
    if "project_id" in kwargs and kwargs["project_id"]:
        project_id = kwargs["project_id"]
        query = query.join(UserProject).filter(UserProject.project_id == project_id)

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


def update_user(db: Session, user_id: uuid.UUID, actor_user_id: uuid.UUID | None = None, **updates) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Audit failure
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="user.update_failed",
                actor_user_id=actor_user_id or user_id,
                target_type="user",
                target_id=user_id,
                metadata={"reason": "not_found"},
            )
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    original = {k: getattr(user, k, None) for k in updates.keys() if hasattr(user, k)}
    for key, value in updates.items():
        if hasattr(user, key):
            setattr(user, key, value)
    try:
        db.commit()
        db.refresh(user)
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
    except Exception as e:
        db.rollback()
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="user.update_failed",
                actor_user_id=actor_user_id or user_id,
                target_type="user",
                target_id=user_id,
                metadata={"reason": "exception", "detail": str(e)},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User update failed: {str(e)}",
        )


def create_user(db: Session, actor_user_id: uuid.UUID | None = None, **user_data) -> User:
    user = User(**user_data)
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
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
    except Exception as e:
        db.rollback()
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="user.create_failed",
                actor_user_id=actor_user_id or uuid.uuid4(),
                target_type="user",
                target_id=None,
                metadata={"reason": "exception", "detail": str(e)},
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User creation failed: {str(e)}",
        )


def delete_user(db: Session, user_id: uuid.UUID, actor_user_id: uuid.UUID | None = None) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        db.query(UserProject).filter(UserProject.user_id == user_id).delete()

        # 2. Delete user's meetings (soft delete) - only update meetings that are not already deleted
        db.query(Meeting).filter(Meeting.created_by == user_id, Meeting.is_deleted == False).update({"is_deleted": True})

        # 3. Delete user's files (hard delete from database, keep in MinIO)
        user_files = db.query(File).filter(File.uploaded_by == user_id).all()
        for file in user_files:
            # Delete from MinIO if needed
            delete_file_from_minio(settings.MINIO_BUCKET_NAME, str(file.id))

            # Delete from database
            db.delete(file)

        user_projects = db.query(Project).filter(Project.created_by == user_id).all()
        for project in user_projects:
            # Delete project with proper cascade handling (inline to avoid circular import)
            project_id = project.id
            from app.models.integration import Integration

            # Delete UserProject relationships
            db.query(UserProject).filter(UserProject.project_id == project_id).delete()

            # Delete ProjectMeeting relationships
            db.query(ProjectMeeting).filter(ProjectMeeting.project_id == project_id).delete()

            # Delete TaskProject relationships
            db.query(TaskProject).filter(TaskProject.project_id == project_id).delete()

            # Delete Integrations
            db.query(Integration).filter(Integration.project_id == project_id).delete()

            # Update Files - set project_id to NULL
            db.query(File).filter(File.project_id == project_id).update({"project_id": None})

            # Finally delete the project
            db.delete(project)

        # 5. Delete user's tasks
        db.query(Task).filter(Task.creator_id == user_id).delete()
        db.query(Task).filter(Task.assignee_id == user_id).delete()

        # 6. Delete user's notifications
        from app.models.notification import Notification

        db.query(Notification).filter(Notification.user_id == user_id).delete()

        # 7. Delete user's integrations
        from app.models.integration import Integration

        db.query(Integration).filter(Integration.project_id.in_(db.query(Project.id).filter(Project.created_by == user_id))).delete()

        # 8. Finally delete the user
        db.delete(user)
        db.commit()
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="user.deleted",
                actor_user_id=actor_user_id or user_id,
                target_type="user",
                target_id=user_id,
                metadata={},
            )
        )
        return True

    except Exception as e:
        db.rollback()
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
            detail=f"User deletion failed: {e}",
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
                results.append({"success": False, "id": user_id, "error": "User not found"})
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
                results.append({"success": False, "id": user_id, "error": "User not found"})
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


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()


def get_user_projects_stats(db: Session, user_id: uuid.UUID) -> dict:
    """Get user's project statistics"""
    from app.models.project import UserProject

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
    """Get or create user device and update FCM token"""
    from datetime import datetime

    from app.models.user import UserDevice

    device = (
        db.query(UserDevice)
        .filter(
            UserDevice.user_id == user_id,
            UserDevice.device_name == device_name,
        )
        .first()
    )

    if device:
        device.fcm_token = fcm_token
        device.device_type = device_type
        device.last_active_at = datetime.utcnow()
        device.is_active = True
    else:
        device = UserDevice(
            user_id=user_id,
            device_name=device_name,
            device_type=device_type,
            fcm_token=fcm_token,
            is_active=True,
        )
        db.add(device)

    db.commit()
    db.refresh(device)
    return device
