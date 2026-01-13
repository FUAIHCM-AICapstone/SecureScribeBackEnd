import uuid
from datetime import datetime
from typing import List, Optional, Tuple

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
        from app.models.project import UserProject
        project_id = kwargs["project_id"]
        query = query.join(UserProject).filter(UserProject.project_id == project_id)
    total = query.count()
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
    users = query.all()
    return users, total


def check_email_exists(db: Session, email: str) -> bool:
    user = db.query(User).filter(User.email == email).first()
    return user is not None


def update_user(db: Session, user_id: uuid.UUID, **updates) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    for key, value in updates.items():
        if hasattr(user, key):
            setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, **user_data) -> User:
    user = User(**user_data)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user_with_cascade(db: Session, user_id: uuid.UUID) -> bool:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    # Delete user's files
    from app.core.config import settings
    from app.models.file import File
    from app.utils.minio import delete_file_from_minio
    user_files = db.query(File).filter(File.uploader_id == user_id).all()
    for file in user_files:
        delete_file_from_minio(settings.MINIO_BUCKET_NAME, str(file.id))
        db.delete(file)

    # Delete user's projects with cascade
    from app.models.meeting import ProjectMeeting
    from app.models.project import Project, UserProject
    from app.models.task import TaskProject
    user_projects = db.query(Project).filter(Project.created_by == user_id).all()
    for project in user_projects:
        project_id = project.id
        db.query(UserProject).filter(UserProject.project_id == project_id).delete()
        db.query(ProjectMeeting).filter(ProjectMeeting.project_id == project_id).delete()
        db.query(TaskProject).filter(TaskProject.project_id == project_id).delete()
        db.query(File).filter(File.project_id == project_id).update({"project_id": None})
        db.delete(project)

    # Delete user's tasks
    from app.models.task import Task
    db.query(Task).filter(Task.creator_id == user_id).delete()
    db.query(Task).filter(Task.assignee_id == user_id).delete()

    # Delete user's notifications
    from app.models.notification import Notification
    db.query(Notification).filter(Notification.user_id == user_id).delete()

    # Finally delete the user
    db.delete(user)
    db.commit()
    return True


def bulk_create_users(db: Session, users_data: List[dict]) -> List[dict]:
    results = []
    for user_data in users_data:
        try:
            if "email" in user_data and check_email_exists(db, user_data["email"]):
                results.append({"success": False, "id": None, "error": "Email already exists"})
                continue
            user = User(**user_data)
            db.add(user)
            db.flush()
            results.append({"success": True, "id": user.id, "error": None})
        except Exception as e:
            results.append({"success": False, "id": None, "error": str(e)})
    db.commit()
    return results


def bulk_update_users(db: Session, updates: List[dict]) -> List[dict]:
    results = []
    for update_item in updates:
        user_id = update_item["id"]
        update_data = update_item["updates"]
        try:
            user = get_user_by_id(db, user_id)
            if not user:
                results.append({"success": False, "id": user_id, "error": "User not found"})
                continue
            for key, value in update_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            results.append({"success": True, "id": user_id, "error": None})
        except Exception as e:
            results.append({"success": False, "id": user_id, "error": str(e)})
    db.commit()
    return results


def bulk_delete_users(db: Session, user_ids: List[uuid.UUID]) -> List[dict]:
    results = []
    for user_id in user_ids:
        try:
            user = get_user_by_id(db, user_id)
            if not user:
                results.append({"success": False, "id": user_id, "error": "User not found"})
                continue
            db.delete(user)
            results.append({"success": True, "id": user_id, "error": None})
        except Exception as e:
            results.append({"success": False, "id": user_id, "error": str(e)})
    db.commit()
    return results


def get_or_create_user_device(db: Session, user_id: uuid.UUID, device_name: str, device_type: str, fcm_token: str):
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
        device.last_active_at = datetime.now()
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
