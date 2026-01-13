import uuid
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.file import (
    crud_check_file_access,
    crud_check_user_project_role,
    crud_create_file,
    crud_delete_file,
    crud_get_file,
    crud_get_files,
    crud_get_project_ids_for_meeting,
    crud_move_file,
    crud_update_file,
)
from app.events.domain_events import BaseDomainEvent, build_diff
from app.models.file import File
from app.schemas.file import FileCreate, FileFilter, FileUpdate
from app.services.meeting import get_meeting
from app.services.project import get_project, is_user_in_project
from app.services.qdrant_service import update_file_vectors_metadata
from app.utils.minio import (
    delete_file_from_minio,
    generate_presigned_url,
    upload_bytes_to_minio,
)


def create_file(db: Session, file_data: FileCreate, uploaded_by: uuid.UUID, file_bytes: bytes) -> Optional[File]:
    # Lazy import to avoid circular import
    from app.services.event_manager import EventManager

    file = crud_create_file(db, **{**file_data.model_dump(), "uploaded_by": uploaded_by})
    upload_result = upload_bytes_to_minio(file_bytes, settings.MINIO_BUCKET_NAME, str(file.id), file_data.mime_type)
    if upload_result:
        # Generate and store presigned URL
        storage_url = generate_presigned_url(settings.MINIO_BUCKET_NAME, str(file.id))
        if storage_url:
            file.storage_url = storage_url
            db.commit()
            db.refresh(file)
            # Emit domain event for upload success
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="file.uploaded",
                    actor_user_id=uploaded_by,
                    target_type="file",
                    target_id=file.id,
                    metadata={
                        "filename": file.filename,
                        "mime_type": file.mime_type,
                        "project_id": str(file.project_id) if file.project_id else None,
                        "meeting_id": str(file.meeting_id) if file.meeting_id else None,
                        "storage_url_present": True,
                    },
                )
            )
            return file
        else:
            # Emit event even if URL missing (still uploaded to storage)
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="file.uploaded",
                    actor_user_id=uploaded_by,
                    target_type="file",
                    target_id=file.id,
                    metadata={
                        "filename": file.filename,
                        "mime_type": file.mime_type,
                        "project_id": str(file.project_id) if file.project_id else None,
                        "meeting_id": str(file.meeting_id) if file.meeting_id else None,
                        "storage_url_present": False,
                    },
                )
            )
            return file
    else:
        # Rollback database changes if MinIO upload fails
        try:
            db.delete(file)
            db.commit()
        finally:
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="file.upload_failed",
                    actor_user_id=uploaded_by,
                    target_type="file",
                    target_id=None,
                    metadata={"reason": "minio_upload_failed", "filename": file_data.filename, "mime_type": file_data.mime_type},
                )
            )
        return None


def get_file(db: Session, file_id: uuid.UUID) -> Optional[File]:
    return crud_get_file(db, file_id)


def get_files(db: Session, filters: Optional[FileFilter] = None, page: int = 1, limit: int = 20, user_id: Optional[uuid.UUID] = None) -> Tuple[List[File], int]:
    return crud_get_files(db, filters.model_dump() if filters else None, page=page, limit=limit, user_id=user_id)


def update_file(db: Session, file_id: uuid.UUID, updates: FileUpdate, actor_user_id: uuid.UUID | None = None) -> Optional[File]:
    # Lazy import to avoid circular import
    from app.services.event_manager import EventManager

    file = crud_get_file(db, file_id)
    if not file:
        EventManager.emit_domain_event(BaseDomainEvent(event_name="file.update_failed", actor_user_id=actor_user_id or uuid.uuid4(), target_type="file", target_id=file_id, metadata={"reason": "not_found"}))
        return None
    update_data = updates.model_dump(exclude_unset=True)
    original = {k: getattr(file, k, None) for k in update_data.keys()}
    file = crud_update_file(db, file_id, **update_data)
    diff = build_diff(original, {k: getattr(file, k, None) for k in update_data.keys()})
    if diff:
        EventManager.emit_domain_event(BaseDomainEvent(event_name="file.updated", actor_user_id=actor_user_id or file.uploaded_by, target_type="file", target_id=file.id, metadata={"diff": diff}))
    return file


def delete_file(db: Session, file_id: uuid.UUID, actor_user_id: uuid.UUID | None = None) -> bool:
    # Lazy import to avoid circular import
    from app.services.event_manager import EventManager

    file = crud_get_file(db, file_id)
    if not file:
        EventManager.emit_domain_event(BaseDomainEvent(event_name="file.delete_failed", actor_user_id=actor_user_id or uuid.uuid4(), target_type="file", target_id=file_id, metadata={"reason": "not_found"}))
        return False
    delete_file_from_minio(settings.MINIO_BUCKET_NAME, str(file.id))
    crud_delete_file(db, file_id)
    EventManager.emit_domain_event(BaseDomainEvent(event_name="file.deleted", actor_user_id=actor_user_id or file.uploaded_by, target_type="file", target_id=file_id, metadata={}))
    return True


def bulk_delete_files(db: Session, file_ids: List[uuid.UUID], user_id: Optional[uuid.UUID] = None) -> List[dict]:
    results = []
    for file_id in file_ids:
        success = delete_file(db, file_id, user_id)
        results.append({"success": success, "file_id": str(file_id)})
    return results


async def bulk_move_files(db: Session, file_ids: List[uuid.UUID], target_project_id: Optional[uuid.UUID] = None, target_meeting_id: Optional[uuid.UUID] = None, user_id: Optional[uuid.UUID] = None) -> List[dict]:
    # Lazy import to avoid circular import
    from app.services.event_manager import EventManager

    results = []
    for file_id in file_ids:
        file = crud_get_file(db, file_id)
        if not file:
            results.append({"success": False, "file_id": str(file_id), "error": "File not found"})
            continue
        old_project_id, old_meeting_id = file.project_id, file.meeting_id
        file = crud_move_file(db, file_id, target_project_id, target_meeting_id)
        vector_update_success = await update_file_vectors_metadata(file_id=str(file_id), project_id=str(target_project_id) if target_project_id else None, meeting_id=str(target_meeting_id) if target_meeting_id else None, owner_user_id=str(user_id) if user_id else None)
        if vector_update_success:
            results.append({"success": True, "file_id": str(file_id)})
            EventManager.emit_domain_event(BaseDomainEvent(event_name="file.moved", actor_user_id=user_id, target_type="file", target_id=file_id, metadata={"old_project_id": str(old_project_id) if old_project_id else None, "new_project_id": str(target_project_id) if target_project_id else None, "old_meeting_id": str(old_meeting_id) if old_meeting_id else None, "new_meeting_id": str(target_meeting_id) if target_meeting_id else None}))
        else:
            results.append({"success": False, "file_id": str(file_id), "error": "Failed to update vector metadata"})
    return results


def check_file_access(db: Session, file: File, user_id: uuid.UUID) -> bool:
    return crud_check_file_access(db, file, user_id)


def check_delete_permissions(db: Session, file: File, current_user_id: uuid.UUID) -> File:
    from fastapi import HTTPException

    if file.uploaded_by == current_user_id:
        return file
    if file.project_id and crud_check_user_project_role(db, current_user_id, file.project_id, ["admin", "owner"]):
        return file
    if file.meeting_id:
        linked_projects = crud_get_project_ids_for_meeting(db, file.meeting_id)
        for project_id in linked_projects:
            if crud_check_user_project_role(db, current_user_id, project_id, ["admin", "owner"]):
                return file
    raise HTTPException(status_code=403, detail="You don't have permission to delete this file")


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
    file = get_file(db, file_id)
    if not file or not check_file_access(db, file, user_id):
        return None, None
    meeting_title = None
    if file.meeting_id:
        meeting = get_meeting(db, file.meeting_id, user_id)
        meeting_title = meeting.title if meeting else None
    return file, meeting_title


async def move_file(db: Session, file: File, project_id: Optional[uuid.UUID], meeting_id: Optional[uuid.UUID], user_id: uuid.UUID) -> Optional[File]:
    """Move file to a project or meeting"""
    old_project_id = file.project_id
    old_meeting_id = file.meeting_id

    # Update file associations
    if project_id is not None:
        file.project_id = project_id
    if meeting_id is not None:
        file.meeting_id = meeting_id

    db.commit()
    db.refresh(file)

    # Update Qdrant vectors with new metadata
    vector_update_success = await update_file_vectors_metadata(
        file_id=str(file.id),
        project_id=str(file.project_id) if file.project_id else None,
        meeting_id=str(file.meeting_id) if file.meeting_id else None,
        owner_user_id=str(user_id),
    )

    if not vector_update_success:
        file.project_id = old_project_id
        file.meeting_id = old_meeting_id
        db.commit()
        return None

    return file
