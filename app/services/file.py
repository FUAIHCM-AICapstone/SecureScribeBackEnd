import uuid
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.file import File
from app.models.project import Project
from app.models.user import User
from app.schemas.file import FileCreate, FileFilter, FileUpdate
from app.utils.minio import delete_file_from_minio, upload_file_to_minio


def create_file(
    db: Session, file_data: FileCreate, uploaded_by: uuid.UUID, file_content: bytes
) -> Optional[File]:
    print(f"DEBUG create_file: file_content type: {type(file_content)}")
    print(
        f"DEBUG create_file: file_content length: {len(file_content) if isinstance(file_content, bytes) else 'N/A'}"
    )

    file = File(**file_data.model_dump(), uploaded_by=uploaded_by)
    db.add(file)
    db.commit()
    db.refresh(file)
    upload_file_to_minio(
        file_content, settings.MINIO_BUCKET_NAME, str(file.id), file.mime_type
    )
    return file


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
    if file.uploaded_by == user_id:
        return True

    if file.project_id:
        return (
            db.query(Project)
            .join(Project.users)
            .filter(Project.id == file.project_id, Project.users.any(user_id=user_id))
            .first()
            is not None
        )

    return False


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


def validate_file_size(file_size: int) -> bool:
    return file_size <= settings.MAX_FILE_SIZE_MB * 1024 * 1024


def validate_file_type(filename: str, mime_type: str) -> bool:
    allowed_extensions = settings.ALLOWED_FILE_EXTENSIONS.split(",")
    allowed_mimes = settings.ALLOWED_MIME_TYPES.split(",")

    file_ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    return file_ext in allowed_extensions and mime_type in allowed_mimes
