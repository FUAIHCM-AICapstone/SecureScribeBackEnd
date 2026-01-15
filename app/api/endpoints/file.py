import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.constants.messages import MessageConstants
from app.core.config import settings
from app.db import get_db
from app.jobs.tasks import index_file_task
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse, create_pagination_meta
from app.schemas.file import (
    FileApiResponse,
    FileCreate,
    FileFilter,
    FileMoveRequest,
    FilesPaginatedResponse,
    FilesWithMeetingPaginatedResponse,
    FilesWithProjectPaginatedResponse,
    FileUpdate,
    FileWithMeeting,
    FileWithProject,
)
from app.services.file import (
    check_delete_permissions,
    check_file_access,
    create_file,
    delete_file,
    get_file,
    get_files,
    get_meeting_files_with_info,
    get_project_files_with_info,
    update_file,
    validate_file,
)
from app.utils.auth import get_current_user
from app.utils.logging import logger

router = APIRouter(prefix=settings.API_V1_STR, tags=["File"])


@router.post("/files/upload", response_model=FileApiResponse)
def upload_file_endpoint(
    file: UploadFile = File(...),
    project_id: Optional[uuid.UUID] = None,
    meeting_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        file_content = file.file.read()
        file_size = len(file_content)

        if not validate_file(file.filename, file.content_type, file_size):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.VALIDATION_ERROR)

        file_data = FileCreate(
            filename=file.filename,
            mime_type=file.content_type,
            size_bytes=file_size,
            file_type="project" if project_id else "meeting",
            project_id=project_id,
            meeting_id=meeting_id,
        )

        new_file = create_file(db, file_data, current_user.id, file_content)
        if not new_file:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)

        # Trigger background indexing for supported file types
        supported_mimes = [
            "text/plain",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
        if file.content_type in supported_mimes:
            logger.info(f"Queuing indexing task for file {new_file.id} ({new_file.filename})")
            try:
                index_file_task.delay(str(new_file.id), str(current_user.id))
                logger.info("Indexing task queued successfully")
            except Exception as e:
                logger.error(f"Failed to queue indexing task: {e}")
        else:
            logger.warning(f"Skipping indexing for unsupported file type: {file.content_type}")

        return ApiResponse(
            success=True,
            message=MessageConstants.FILE_UPLOADED_SUCCESS,
            data={
                "id": new_file.id,
                "filename": new_file.filename,
                "mime_type": new_file.mime_type,
                "size_bytes": new_file.size_bytes,
                "file_type": new_file.file_type,
                "project_id": new_file.project_id,
                "meeting_id": new_file.meeting_id,
                "uploaded_by": new_file.uploaded_by,
                "created_at": new_file.created_at.isoformat(),
                "storage_url": new_file.storage_url,
                "indexing_queued": file.content_type in supported_mimes,
            },
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)


@router.get("/files", response_model=FilesPaginatedResponse)
def get_files_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    limit: int = 20,
    filename: Optional[str] = None,
    file_type: Optional[str] = None,
    project_id: Optional[uuid.UUID] = None,
    meeting_id: Optional[uuid.UUID] = None,
):
    try:
        filters = FileFilter(
            filename=filename,
            file_type=file_type,
            project_id=project_id,
            meeting_id=meeting_id,
        )

        files, total = get_files(db, filters, page, limit, current_user.id)

        pagination_meta = create_pagination_meta(page, limit, total)

        return PaginatedResponse(
            success=True,
            message=MessageConstants.FILE_RETRIEVED_SUCCESS,
            data=[
                {
                    "id": file.id,
                    "filename": file.filename,
                    "mime_type": file.mime_type,
                    "size_bytes": file.size_bytes,
                    "file_type": file.file_type,
                    "project_id": file.project_id,
                    "meeting_id": file.meeting_id,
                    "uploaded_by": file.uploaded_by,
                    "created_at": file.created_at.isoformat(),
                    "storage_url": file.storage_url,
                }
                for file in files
            ],
            pagination=pagination_meta,
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)


@router.get("/files/{file_id}", response_model=FileApiResponse)
def get_file_endpoint(
    file_id: uuid.UUID,
    download: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        file = get_file(db, file_id)
        if not file:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageConstants.FILE_NOT_FOUND)

        if not check_file_access(db, file, current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MessageConstants.ACCESS_DENIED)

        # If download requested, stream the file
        if download:
            from app.utils.minio import get_minio_client

            try:
                client = get_minio_client()
                response = client.get_object(settings.MINIO_BUCKET_NAME, str(file.id))
                return StreamingResponse(response, media_type=file.mime_type, headers={"Content-Disposition": f"attachment; filename={file.filename}"})
            except Exception as e:
                logger.exception(f"File download error: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Download failed")

        return ApiResponse(
            success=True,
            message=MessageConstants.FILE_RETRIEVED_SUCCESS,
            data={
                "id": file.id,
                "filename": file.filename,
                "mime_type": file.mime_type,
                "size_bytes": file.size_bytes,
                "file_type": file.file_type,
                "project_id": file.project_id,
                "meeting_id": file.meeting_id,
                "uploaded_by": file.uploaded_by,
                "created_at": file.created_at.isoformat(),
                "storage_url": file.storage_url,
            },
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)


@router.put("/files/{file_id}", response_model=FileApiResponse)
def update_file_endpoint(
    file_id: uuid.UUID,
    updates: FileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        file = get_file(db, file_id)
        if not file:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageConstants.FILE_NOT_FOUND)

        check_delete_permissions(db, file, current_user.id)

        updated_file = update_file(db, file_id, updates)
        if not updated_file:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)

        return ApiResponse(
            success=True,
            message=MessageConstants.OPERATION_SUCCESSFUL,
            data={
                "id": updated_file.id,
                "filename": updated_file.filename,
                "mime_type": updated_file.mime_type,
                "size_bytes": updated_file.size_bytes,
                "file_type": updated_file.file_type,
                "project_id": updated_file.project_id,
                "meeting_id": updated_file.meeting_id,
                "uploaded_by": updated_file.uploaded_by,
                "created_at": updated_file.created_at.isoformat(),
                "storage_url": updated_file.storage_url,
            },
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)


@router.post("/files/{file_id}/move", response_model=FileApiResponse)
async def move_file_endpoint(
    file_id: uuid.UUID,
    move_request: FileMoveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move a file to a project or meeting"""
    try:
        file = get_file(db, file_id)
        if not file:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageConstants.FILE_NOT_FOUND)

        check_delete_permissions(db, file, current_user.id)

        # Check if user has access to target project/meeting
        if move_request.project_id:
            from app.services.project import is_user_in_project

            if not is_user_in_project(db, move_request.project_id, current_user.id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MessageConstants.ACCESS_DENIED)

        if move_request.meeting_id:
            from app.services.meeting import get_meeting

            target_meeting = get_meeting(db, move_request.meeting_id, current_user.id)
            if not target_meeting:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MessageConstants.ACCESS_DENIED)

        # Move file using service layer
        from app.services.file import move_file as move_file_service

        moved_file = await move_file_service(db, file, move_request.project_id, move_request.meeting_id, current_user.id)
        if not moved_file:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)

        return ApiResponse(
            success=True,
            message=MessageConstants.OPERATION_SUCCESSFUL,
            data={
                "id": moved_file.id,
                "filename": moved_file.filename,
                "mime_type": moved_file.mime_type,
                "size_bytes": moved_file.size_bytes,
                "file_type": moved_file.file_type,
                "project_id": moved_file.project_id,
                "meeting_id": moved_file.meeting_id,
                "uploaded_by": moved_file.uploaded_by,
                "created_at": moved_file.created_at.isoformat(),
                "storage_url": moved_file.storage_url,
            },
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)


@router.delete("/files/{file_id}", response_model=ApiResponse[dict])
def delete_file_endpoint(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        file = get_file(db, file_id)
        if not file:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageConstants.FILE_NOT_FOUND)

        check_delete_permissions(db, file, current_user.id)

        success = delete_file(db, file_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)

        return ApiResponse(success=True, message=MessageConstants.FILE_DELETED_SUCCESS, data={})
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)


@router.get("/projects/{project_id}/files", response_model=FilesWithProjectPaginatedResponse)
def get_project_files_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    filename: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    page: int = 1,
    limit: int = 20,
):
    """Get files for a specific project with project info"""
    try:
        files, project_name, total = get_project_files_with_info(db, project_id, current_user.id, page, limit, filename)

        if files is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MessageConstants.ACCESS_DENIED)

        pagination_meta = create_pagination_meta(page, limit, total)

        return PaginatedResponse(
            success=True,
            message=MessageConstants.FILE_RETRIEVED_SUCCESS,
            data=[
                FileWithProject(
                    **file.__dict__,
                    project_name=project_name,
                    can_access=True,
                )
                for file in files
            ],
            pagination=pagination_meta,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)


@router.get("/meetings/{meeting_id}/files", response_model=FilesWithMeetingPaginatedResponse)
def get_meeting_files_endpoint(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    limit: int = 20,
):
    """Get files for a specific meeting with meeting info"""
    try:
        files, meeting_title, total = get_meeting_files_with_info(db, meeting_id, current_user.id, page, limit)

        if files is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageConstants.MEETING_NOT_FOUND)

        pagination_meta = create_pagination_meta(page, limit, total)

        return PaginatedResponse(
            success=True,
            message=MessageConstants.FILE_RETRIEVED_SUCCESS,
            data=[
                FileWithMeeting(
                    **file.__dict__,
                    meeting_title=meeting_title,
                    can_access=True,
                )
                for file in files
            ],
            pagination=pagination_meta,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)
