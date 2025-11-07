import uuid
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.file import File
from app.models.meeting import Meeting
from app.models.project import Project, UserProject
from app.schemas.file import FileCreate, FileFilter, FileUpdate
from app.utils.meeting import check_meeting_access as check_meeting_access_utils
from app.utils.minio import (
    delete_file_from_minio,
    generate_presigned_url,
    upload_bytes_to_minio,
)


def create_file(db: Session, file_data: FileCreate, uploaded_by: uuid.UUID, file_bytes: bytes) -> Optional[File]:
    file = File(**file_data.model_dump(), uploaded_by=uploaded_by)
    db.add(file)
    db.commit()
    db.refresh(file)
    upload_result = upload_bytes_to_minio(file_bytes, settings.MINIO_BUCKET_NAME, str(file.id), file_data.mime_type)
    if upload_result:
        # Generate and store presigned URL
        storage_url = generate_presigned_url(settings.MINIO_BUCKET_NAME, str(file.id))
        if storage_url:
            file.storage_url = storage_url
            db.commit()
            db.refresh(file)
            return file
        else:
            return file
    else:
        # Rollback database changes if MinIO upload fails
        db.delete(file)
        db.commit()
        return None


def get_file(db: Session, file_id: uuid.UUID) -> Optional[File]:
    return db.query(File).filter(File.id == file_id).first()


def get_files(
    db: Session,
    filters: Optional[FileFilter] = None,
    page: int = 1,
    limit: int = 20,
    user_id: Optional[uuid.UUID] = None,
) -> Tuple[List[File], int]:
    query = db.query(File)
    if filters:
        if filters.filename:
            query = query.filter(File.filename.ilike(f"%{filters.filename}%"))
        if filters.mime_type:
            query = query.filter(File.mime_type == filters.mime_type)
        if filters.file_type:
            query = query.filter(File.file_type == filters.file_type)
        if filters.project_id:
            query = query.filter(File.project_id == filters.project_id)
        if filters.meeting_id:
            query = query.filter(File.meeting_id == filters.meeting_id)
        if filters.uploaded_by:
            query = query.filter(File.uploaded_by == filters.uploaded_by)
    if user_id:
        # Get all projects the user has access to
        user_projects = db.query(Project.id).join(Project.users).filter(Project.users.any(user_id=user_id)).subquery()
        # Get all meetings the user has access to (through projects)
        from app.models.meeting import Meeting, ProjectMeeting

        user_meetings = db.query(Meeting.id).join(ProjectMeeting, Meeting.id == ProjectMeeting.meeting_id).join(Project, ProjectMeeting.project_id == Project.id).join(Project.users).filter(Project.users.any(user_id=user_id), Meeting.is_deleted == False).subquery()
        # Filter files to only include those the user has access to
        query = query.filter(
            # Files uploaded by the user (personal files)
            (File.uploaded_by == user_id)
            |
            # Files that belong to projects the user has access to
            (File.project_id.in_(user_projects))
            |
            # Files that belong to meetings the user has access to
            (File.meeting_id.in_(user_meetings))
        )
    total = query.count()
    files = query.offset((page - 1) * limit).limit(limit).all()
    return files, total


def update_file(db: Session, file_id: uuid.UUID, updates: FileUpdate) -> Optional[File]:
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        return None
    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(file, key, value)
    db.commit()
    db.refresh(file)
    return file


def delete_file(db: Session, file_id: uuid.UUID) -> bool:
    file = db.query(File).filter(File.id == file_id).first()
    if not file:
        return False
    delete_file_from_minio(settings.MINIO_BUCKET_NAME, str(file.id))
    db.delete(file)
    db.commit()
    return True


def bulk_delete_files(db: Session, file_ids: List[uuid.UUID], user_id: Optional[uuid.UUID] = None) -> List[dict]:
    results = []
    for file_id in file_ids:
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            results.append({"success": False, "file_id": str(file_id), "error": "File not found"})
            continue
        # Check user access if user_id is provided
        if user_id and not check_file_access(db, file, user_id):
            results.append({"success": False, "file_id": str(file_id), "error": "Access denied"})
            continue
        delete_file_from_minio(settings.MINIO_BUCKET_NAME, str(file.id))
        db.delete(file)
        results.append({"success": True, "file_id": str(file_id)})
    db.commit()
    return results


async def bulk_move_files(
    db: Session,
    file_ids: List[uuid.UUID],
    target_project_id: Optional[uuid.UUID] = None,
    target_meeting_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
) -> List[dict]:
    from app.services.qdrant_service import update_file_vectors_metadata

    results = []
    for file_id in file_ids:
        file = db.query(File).filter(File.id == file_id).first()
        if not file:
            results.append({"success": False, "file_id": str(file_id), "error": "File not found"})
            continue
        # Check user access if user_id is provided
        if user_id and not check_file_access(db, file, user_id):
            results.append({"success": False, "file_id": str(file_id), "error": "Access denied"})
            continue
        # Check if user has access to target project/meeting
        if target_project_id:
            from app.services.project import is_user_in_project

            if not is_user_in_project(db, target_project_id, user_id):
                results.append(
                    {
                        "success": False,
                        "file_id": str(file_id),
                        "error": "Access denied to target project",
                    }
                )
                continue
        if target_meeting_id:
            target_meeting = db.query(Meeting).filter(Meeting.id == target_meeting_id, Meeting.is_deleted == False).first()
            if not target_meeting or not check_meeting_access_utils(db, target_meeting, user_id):
                results.append(
                    {
                        "success": False,
                        "file_id": str(file_id),
                        "error": "Access denied to target meeting",
                    }
                )
                continue
        if target_project_id is not None:
            file.project_id = target_project_id
        if target_meeting_id is not None:
            file.meeting_id = target_meeting_id

        # Update Qdrant vectors with new metadata
        vector_update_success = await update_file_vectors_metadata(
            file_id=str(file_id),
            project_id=str(target_project_id) if target_project_id else None,
            meeting_id=str(target_meeting_id) if target_meeting_id else None,
            owner_user_id=str(user_id) if user_id else None,
        )

        if not vector_update_success:
            results.append({"success": False, "file_id": str(file_id), "error": "Failed to update vector metadata"})
            continue

        results.append({"success": True, "file_id": str(file_id)})
    db.commit()
    return results


def check_file_access(db: Session, file: File, user_id: uuid.UUID) -> bool:
    """Check if user has access to a file"""
    # User owns the file
    if file.uploaded_by == user_id:
        return True
    # File belongs to a project - check project membership
    if file.project_id:
        return db.query(Project).join(Project.users).filter(Project.id == file.project_id, Project.users.any(user_id=user_id)).first() is not None
    return False


def check_delete_permissions(db: Session, file: File, current_user_id: uuid.UUID) -> File:
    """Check if user can delete file and raise HTTPException if not.

    Permission rules:
    - File owner (uploaded_by) can always delete their own file
    - If file has project_id: project admin/owner can delete
    - If file has meeting_id: user must be admin/owner of a project linked to the meeting
    """
    from fastapi import HTTPException

    # Rule 1: File owner can always delete
    if file.uploaded_by == current_user_id:
        return file

    # Rule 2: Project admin/owner can delete files in their project
    if file.project_id:
        user_project = (
            db.query(UserProject)
            .filter(
                UserProject.user_id == current_user_id,
                UserProject.project_id == file.project_id,
                UserProject.role.in_(["admin", "owner"]),
            )
            .first()
        )
        if user_project:
            return file

    # Rule 3: For meeting files, check if user is admin/owner of linked project
    if file.meeting_id:
        from app.models.meeting import ProjectMeeting

        linked_projects = db.query(ProjectMeeting.project_id).filter(ProjectMeeting.meeting_id == file.meeting_id).all()

        for (project_id,) in linked_projects:
            user_project = (
                db.query(UserProject)
                .filter(
                    UserProject.user_id == current_user_id,
                    UserProject.project_id == project_id,
                    UserProject.role.in_(["admin", "owner"]),
                )
                .first()
            )
            if user_project:
                return file

    # No permission found
    raise HTTPException(
        status_code=403,
        detail="You don't have permission to delete this file",
    )


def validate_file(filename: str, mime_type: str, file_size: int) -> bool:
    """Validate file size and type in single function"""
    # Check file size
    if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
        return False
    # Check file type
    allowed_extensions = settings.ALLOWED_FILE_EXTENSIONS.split(",")
    allowed_mimes = settings.ALLOWED_MIME_TYPES.split(",")
    file_ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    return file_ext in allowed_extensions and mime_type in allowed_mimes


def get_project_files_with_info(
    db: Session,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    limit: int = 20,
    filename: Optional[str] = None,
) -> Tuple[List[File], str, int]:
    """Get files for a project with project name and pagination"""
    from app.services.project import get_project, is_user_in_project

    # Check access
    if not is_user_in_project(db, project_id, user_id):
        return [], None, 0
    # Get project name
    project = get_project(db, project_id)
    project_name = project.name if project else None
    # Get files
    filters = FileFilter(project_id=project_id, filename=filename)
    files, total = get_files(db, filters, page, limit, user_id)
    return files, project_name, total


def get_meeting_files_with_info(
    db: Session,
    meeting_id: uuid.UUID,
    user_id: uuid.UUID,
    page: int = 1,
    limit: int = 20,
) -> Tuple[List[File], str, int]:
    """Get files for a meeting with meeting title and pagination"""
    from app.services.meeting import get_meeting

    # Get meeting with access check
    meeting = get_meeting(db, meeting_id, user_id)
    if not meeting:
        return [], None, 0
    meeting_title = meeting.title
    # Get files
    filters = FileFilter(meeting_id=meeting_id)
    files, total = get_files(db, filters, page, limit, user_id)
    return files, meeting_title, total


def get_file_with_project_info(db: Session, file_id: uuid.UUID, user_id: uuid.UUID) -> Tuple[Optional[File], Optional[str]]:
    """Get a file with its project information"""
    from app.services.project import get_project

    file = get_file(db, file_id)
    if not file or not check_file_access(db, file, user_id):
        return None, None
    project_name = None
    if file.project_id:
        project = get_project(db, file.project_id)
        project_name = project.name if project else None
    return file, project_name


def get_file_with_meeting_info(db: Session, file_id: uuid.UUID, user_id: uuid.UUID) -> Tuple[Optional[File], Optional[str]]:
    """Get a file with its meeting information"""
    from app.services.meeting import get_meeting

    file = get_file(db, file_id)
    if not file or not check_file_access(db, file, user_id):
        return None, None
    meeting_title = None
    if file.meeting_id:
        meeting = get_meeting(db, file.meeting_id, user_id)
        meeting_title = meeting.title if meeting else None
    return file, meeting_title
