import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.jobs.tasks import index_file_task
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse, create_pagination_meta
from app.schemas.file import (
    BulkFileOperation,
    BulkFileResponse,
    FileApiResponse,
    FileCreate,
    FileFilter,
    FileMoveRequest,
    FilesPaginatedResponse,
    FilesWithMeetingPaginatedResponse,
    FilesWithProjectPaginatedResponse,
    FileUpdate,
    FileWithMeeting,
    FileWithMeetingApiResponse,
    FileWithProject,
    FileWithProjectApiResponse,
)
from app.services.file import (
    bulk_delete_files,
    bulk_move_files,
    check_file_access,
    create_file,
    delete_file,
    get_file,
    get_file_with_meeting_info,
    get_file_with_project_info,
    get_files,
    get_meeting_files_with_info,
    get_project_files_with_info,
    update_file,
    validate_file,
)
from app.utils.auth import get_current_user

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
            raise HTTPException(status_code=400, detail="File validation failed")

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
            raise HTTPException(status_code=400, detail="Failed to upload file")

        # Trigger background indexing for supported file types
        supported_mimes = [
            "text/plain",
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
        if file.content_type in supported_mimes:
            print(f"\033[94m🚀 Queuing indexing task for file {new_file.id} ({new_file.filename})\033[0m")
            try:
                index_file_task.delay(str(new_file.id), str(current_user.id))
                print("\033[92m✅ Indexing task queued successfully\033[0m")
            except Exception as e:
                print(f"\033[91m❌ Failed to queue indexing task: {e}\033[0m")
        else:
            print(f"\033[93m⚠️ Skipping indexing for unsupported file type: {file.content_type}\033[0m")

        return ApiResponse(
            success=True,
            message="File uploaded successfully",
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
            message="Files retrieved successfully",
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/files/{file_id}", response_model=FileApiResponse)
def get_file_endpoint(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        file = get_file(db, file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        if not check_file_access(db, file, current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        return ApiResponse(
            success=True,
            message="File retrieved successfully",
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
            raise HTTPException(status_code=404, detail="File not found")

        if file.uploaded_by != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        updated_file = update_file(db, file_id, updates)
        if not updated_file:
            raise HTTPException(status_code=400, detail="Failed to update file")

        return ApiResponse(
            success=True,
            message="File updated successfully",
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
            raise HTTPException(status_code=404, detail="File not found")

        if file.uploaded_by != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Check if user has access to target project/meeting
        if move_request.project_id:
            from app.services.project import is_user_in_project

            if not is_user_in_project(db, move_request.project_id, current_user.id):
                raise HTTPException(status_code=403, detail="Access denied to project")

        if move_request.meeting_id:
            from app.models.meeting import Meeting
            from app.utils.meeting import (
                check_meeting_access as check_meeting_access_utils,
            )

            target_meeting = db.query(Meeting).filter(Meeting.id == move_request.meeting_id, Meeting.is_deleted == False).first()
            if not target_meeting or not check_meeting_access_utils(db, target_meeting, current_user.id):
                raise HTTPException(status_code=403, detail="Access denied to meeting")

        # Store old values for rollback
        old_project_id = file.project_id
        old_meeting_id = file.meeting_id

        # Update file associations
        if move_request.project_id is not None:
            file.project_id = move_request.project_id
        if move_request.meeting_id is not None:
            file.meeting_id = move_request.meeting_id

        db.commit()
        db.refresh(file)

        # Update Qdrant vectors with new metadata
        from app.services.qdrant_service import update_file_vectors_metadata

        vector_update_success = await update_file_vectors_metadata(
            file_id=str(file_id),
            project_id=str(file.project_id) if file.project_id else None,
            meeting_id=str(file.meeting_id) if file.meeting_id else None,
            owner_user_id=str(current_user.id),
        )

        if not vector_update_success:
            file.project_id = old_project_id
            file.meeting_id = old_meeting_id
            db.commit()
            raise HTTPException(status_code=400, detail="Failed to update vector metadata")

        return ApiResponse(
            success=True,
            message="File moved successfully",
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/files/{file_id}", response_model=ApiResponse[dict])
def delete_file_endpoint(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        file = get_file(db, file_id)
        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        if file.uploaded_by != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        success = delete_file(db, file_id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to delete file")

        return ApiResponse(success=True, message="File deleted successfully", data={})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/files/bulk", response_model=BulkFileResponse)
async def bulk_files_endpoint(
    operation: BulkFileOperation,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    try:
        # Execute bulk operation
        if operation.operation == "delete":
            results = bulk_delete_files(db, operation.file_ids, _current_user.id)
        elif operation.operation == "move":
            results = await bulk_move_files(
                db,
                operation.file_ids,
                operation.target_project_id,
                operation.target_meeting_id,
                _current_user.id,
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid operation")

        # Calculate statistics
        total_processed = len(results)
        total_success = sum(1 for r in results if r["success"])
        total_failed = total_processed - total_success

        return BulkFileResponse(
            success=total_failed == 0,
            message=f"Bulk {operation.operation} completed. {total_success} successful, {total_failed} failed.",
            data=results,
            total_processed=total_processed,
            total_success=total_success,
            total_failed=total_failed,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/projects/{project_id}/files", response_model=FilesWithProjectPaginatedResponse)
def get_project_files_endpoint(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = 1,
    limit: int = 20,
):
    """Get files for a specific project with project info"""
    try:
        files, project_name, total = get_project_files_with_info(db, project_id, current_user.id, page, limit)

        if files is None:
            raise HTTPException(status_code=403, detail="Access denied")

        pagination_meta = create_pagination_meta(page, limit, total)

        return PaginatedResponse(
            success=True,
            message="Project files retrieved successfully",
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
            raise HTTPException(status_code=404, detail="Meeting not found or access denied")

        pagination_meta = create_pagination_meta(page, limit, total)

        return PaginatedResponse(
            success=True,
            message="Meeting files retrieved successfully",
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
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/files/{file_id}/with-project", response_model=FileWithProjectApiResponse)
def get_file_with_project_endpoint(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a file with project information"""
    try:
        file, project_name = get_file_with_project_info(db, file_id, current_user.id)

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        return ApiResponse(
            success=True,
            message="File with project info retrieved successfully",
            data=FileWithProject(
                **file.__dict__,
                project_name=project_name,
                can_access=True,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/files/{file_id}/with-meeting", response_model=FileWithMeetingApiResponse)
def get_file_with_meeting_endpoint(
    file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a file with meeting information"""
    try:
        file, meeting_title = get_file_with_meeting_info(db, file_id, current_user.id)

        if not file:
            raise HTTPException(status_code=404, detail="File not found")

        return ApiResponse(
            success=True,
            message="File with meeting info retrieved successfully",
            data=FileWithMeeting(
                **file.__dict__,
                meeting_title=meeting_title,
                can_access=True,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
