import uuid
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.file import File
from app.models.meeting import Meeting, ProjectMeeting
from app.models.project import Project, UserProject


def crud_create_file(db: Session, **file_data) -> File:
    file = File(**file_data)
    db.add(file)
    db.commit()
    db.refresh(file)
    return file


def crud_get_file(db: Session, file_id: uuid.UUID) -> Optional[File]:
    return db.query(File).filter(File.id == file_id).first()


def crud_get_files(db: Session, filters: dict = None, **kwargs) -> Tuple[List[File], int]:
    query = db.query(File)
    if filters:
        if "filename" in filters and filters["filename"]:
            query = query.filter(File.filename.ilike(f"%{filters['filename']}%"))
        if "mime_type" in filters and filters["mime_type"]:
            query = query.filter(File.mime_type == filters["mime_type"])
        if "file_type" in filters and filters["file_type"]:
            query = query.filter(File.file_type == filters["file_type"])
        if "project_id" in filters and filters["project_id"]:
            query = query.filter(File.project_id == filters["project_id"])
        if "meeting_id" in filters and filters["meeting_id"]:
            query = query.filter(File.meeting_id == filters["meeting_id"])
        if "uploaded_by" in filters and filters["uploaded_by"]:
            query = query.filter(File.uploaded_by == filters["uploaded_by"])
    user_id = kwargs.get("user_id")
    if user_id:
        user_projects = db.query(Project.id).join(Project.users).filter(Project.users.any(user_id=user_id)).subquery()
        user_meetings = db.query(Meeting.id).join(ProjectMeeting, Meeting.id == ProjectMeeting.meeting_id).join(Project, ProjectMeeting.project_id == Project.id).join(Project.users).filter(Project.users.any(user_id=user_id), Meeting.is_deleted == False).subquery()
        query = query.filter((File.uploaded_by == user_id) | (File.project_id.in_(user_projects)) | (File.meeting_id.in_(user_meetings)))
    total = query.count()
    page = int(kwargs.get("page", 1))
    limit = int(kwargs.get("limit", 20))
    files = query.offset((page - 1) * limit).limit(limit).all()
    return files, total


def crud_update_file(db: Session, file_id: uuid.UUID, **updates) -> Optional[File]:
    file = crud_get_file(db, file_id)
    if not file:
        return None
    for key, value in updates.items():
        if hasattr(file, key):
            setattr(file, key, value)
    db.commit()
    db.refresh(file)
    return file


def crud_delete_file(db: Session, file_id: uuid.UUID) -> bool:
    file = crud_get_file(db, file_id)
    if not file:
        return False
    db.delete(file)
    db.commit()
    return True


def crud_move_file(db: Session, file_id: uuid.UUID, target_project_id: Optional[uuid.UUID] = None, target_meeting_id: Optional[uuid.UUID] = None) -> Optional[File]:
    file = crud_get_file(db, file_id)
    if not file:
        return None
    if target_project_id is not None:
        file.project_id = target_project_id
    if target_meeting_id is not None:
        file.meeting_id = target_meeting_id
    db.commit()
    db.refresh(file)
    return file


def crud_check_file_access(db: Session, file: File, user_id: uuid.UUID) -> bool:
    if file.uploaded_by == user_id:
        return True
    if file.project_id:
        return db.query(Project).join(Project.users).filter(Project.id == file.project_id, Project.users.any(user_id=user_id)).first() is not None
    return False


def crud_check_user_project_role(db: Session, user_id: uuid.UUID, project_id: uuid.UUID, roles: List[str]) -> bool:
    return db.query(UserProject).filter(UserProject.user_id == user_id, UserProject.project_id == project_id, UserProject.role.in_(roles)).first() is not None


def crud_get_project_ids_for_meeting(db: Session, meeting_id: uuid.UUID) -> List[uuid.UUID]:
    return [id for (id,) in db.query(ProjectMeeting.project_id).filter(ProjectMeeting.meeting_id == meeting_id).all()]
