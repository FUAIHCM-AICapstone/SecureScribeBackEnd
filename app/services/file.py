import uuid
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.file import File
from app.models.project import Project
from app.schemas.file import FileCreate, FileFilter, FileUpdate
from app.utils.minio import (
    delete_file_from_minio,
    generate_presigned_url,
    upload_bytes_to_minio,
)


def create_file(
    db: Session, file_data: FileCreate, uploaded_by: uuid.UUID, file_bytes: bytes
) -> Optional[File]:
    file = File(**file_data.model_dump(), uploaded_by=uploaded_by)
    db.add(file)
    db.commit()
    db.refresh(file)

    upload_result = upload_bytes_to_minio(
        file_bytes, settings.MINIO_BUCKET_NAME, str(file.id), file_data.mime_type
    )

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
        query = query.filter(
            (File.project_id.is_(None))
            | (
                File.project_id.in_(
                    db.query(Project.id)
                    .join(Project.users)
                    .filter(Project.users.any(user_id=user_id))
                )
            )
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


def bulk_delete_files(db: Session, file_ids: List[uuid.UUID]) -> List[dict]:
    results = []
    for file_id in file_ids:
        file = db.query(File).filter(File.id == file_id).first()
        if file:
            delete_file_from_minio(settings.MINIO_BUCKET_NAME, str(file.id))
            db.delete(file)
            results.append({"success": True, "file_id": str(file_id)})
        else:
            results.append(
                {"success": False, "file_id": str(file_id), "error": "File not found"}
            )

    db.commit()
    return results


def bulk_move_files(
    db: Session,
    file_ids: List[uuid.UUID],
    target_project_id: Optional[uuid.UUID] = None,
    target_meeting_id: Optional[uuid.UUID] = None,
) -> List[dict]:
    results = []
    for file_id in file_ids:
        file = db.query(File).filter(File.id == file_id).first()
        if file:
            if target_project_id is not None:
                file.project_id = target_project_id
            if target_meeting_id is not None:
                file.meeting_id = target_meeting_id
            results.append({"success": True, "file_id": str(file_id)})
        else:
            results.append(
                {"success": False, "file_id": str(file_id), "error": "File not found"}
            )

    db.commit()
    return results


def check_file_access(db: Session, file: File, user_id: uuid.UUID) -> bool:
    """Check if user has access to a file"""
    # User owns the file
    if file.uploaded_by == user_id:
        return True

    # File belongs to a project - check project membership
    if file.project_id:
        return (
            db.query(Project)
            .join(Project.users)
            .filter(Project.id == file.project_id, Project.users.any(user_id=user_id))
            .first()
            is not None
        )

    return False


def check_meeting_access(
    db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    """Check if user has access to a meeting's files"""
    from app.models.meeting import Meeting, ProjectMeeting
    from app.models.project import UserProject

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.is_deleted == False).first()
    if not meeting:
        return False

    # Personal meeting created by the user
    if meeting.is_personal and meeting.created_by == user_id:
        return True

    # Check if user is a member of any project linked to this meeting
    linked_project_membership = (
        db.query(ProjectMeeting)
        .join(
            UserProject,
            UserProject.project_id == ProjectMeeting.project_id,
        )
        .filter(
            ProjectMeeting.meeting_id == meeting_id,
            UserProject.user_id == user_id,
        )
        .first()
        is not None
    )

    return linked_project_membership


def extract_text_from_file(file_content: bytes, mime_type: str) -> Optional[str]:
    if mime_type == "text/plain":
        return file_content.decode("utf-8", errors="ignore")

    if mime_type == "application/pdf":
        try:
            import PyPDF2

            pdf_reader = PyPDF2.PdfReader(file_content)
            return " ".join(page.extract_text() for page in pdf_reader.pages)
        except ImportError:
            return None

    if (
        mime_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        try:
            from docx import Document

            doc = Document(file_content)
            return " ".join(paragraph.text for paragraph in doc.paragraphs)
        except ImportError:
            return None

    return None


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
