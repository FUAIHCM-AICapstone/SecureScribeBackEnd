import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.jobs.tasks import process_audio_task
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse, create_pagination_meta
from app.schemas.meeting import (
    AudioFileItem,
    MeetingApiResponse,
    MeetingAudioFilesPaginatedResponse,
    MeetingCreate,
    MeetingFilter,
    MeetingsPaginatedResponse,
    MeetingUpdate,
    MeetingWithProjectsApiResponse,
)
from app.services.meeting import (
    add_meeting_to_project,
    check_delete_permissions,
    create_audio_file,
    create_meeting,
    delete_meeting,
    get_meeting,
    get_meeting_audio_files,
    get_meetings,
    remove_meeting_from_project,
    update_meeting,
    validate_meeting_for_audio_operations,
)
from app.utils.auth import get_current_user
from app.utils.meeting import get_meeting_projects

router = APIRouter(prefix=settings.API_V1_STR, tags=["Meeting"])


@router.post("/meetings", response_model=MeetingApiResponse)
def create_meeting_endpoint(
    meeting: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new meeting"""
    try:
        new_meeting = create_meeting(db, meeting, current_user.id)
        response_data = {
            "id": new_meeting.id,
            "title": new_meeting.title,
            "description": new_meeting.description,
            "url": new_meeting.url,
            "start_time": new_meeting.start_time,
            "created_by": new_meeting.created_by,
            "is_personal": new_meeting.is_personal,
            "status": new_meeting.status,
            "is_deleted": new_meeting.is_deleted,
            "created_at": new_meeting.created_at,
            "updated_at": new_meeting.updated_at,
            "projects": [],
            "can_access": True,
        }

        return ApiResponse(
            success=True,
            message="Meeting created successfully",
            data=response_data,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/meetings", response_model=MeetingsPaginatedResponse)
def get_meetings_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    title: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_personal: Optional[bool] = Query(None),
    created_by: Optional[str] = Query(None),
    tag_ids: str = Query("", description="Comma-separated tag IDs"),
):
    """Get meetings with filtering and pagination"""
    try:
        # Parse UUID fields
        created_by_uuid = None
        if created_by:
            try:
                created_by_uuid = uuid.UUID(created_by)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid created_by UUID format")

        # Parse tag IDs
        tag_id_list = []
        if tag_ids.strip():
            tag_id_list = [uuid.UUID(tid.strip()) for tid in tag_ids.split(",") if tid.strip()]

        # Create filter object
        filters = MeetingFilter(
            title=title,
            status=status,
            is_personal=is_personal,
            created_by=created_by_uuid,
            tag_ids=tag_id_list,
        )

        meetings, total = get_meetings(db=db, user_id=current_user.id, filters=filters, page=page, limit=limit)

        # Format response data
        meetings_data = []
        for meeting in meetings:
            _ = get_meeting_projects(db, meeting.id)
            meetings_data.append(
                {
                    "id": meeting.id,
                    "title": meeting.title,
                    "description": meeting.description,
                    "url": meeting.url,
                    "start_time": meeting.start_time,
                    "created_by": meeting.created_by,
                    "is_personal": meeting.is_personal,
                    "status": meeting.status,
                    "is_deleted": meeting.is_deleted,
                    "created_at": meeting.created_at,
                    "updated_at": meeting.updated_at,
                    "projects": [],
                    "can_access": True,
                }
            )

        pagination_meta = create_pagination_meta(page, limit, total)

        return PaginatedResponse(
            success=True,
            message="Meetings retrieved successfully",
            data=meetings_data,
            pagination=pagination_meta,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/meetings/{meeting_id}", response_model=MeetingWithProjectsApiResponse)
def get_meeting_endpoint(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific meeting by ID"""
    try:
        meeting = get_meeting(db, meeting_id, current_user.id, raise_404=True)
        projects = get_meeting_projects(db, meeting.id)
        response_data = {
            "id": meeting.id,
            "title": meeting.title,
            "description": meeting.description,
            "url": meeting.url,
            "start_time": meeting.start_time,
            "created_by": meeting.created_by,
            "is_personal": meeting.is_personal,
            "status": meeting.status,
            "is_deleted": meeting.is_deleted,
            "created_at": meeting.created_at,
            "updated_at": meeting.updated_at,
            "projects": [],
            "can_access": True,
            "project_count": len(projects),
            "member_count": 0,
        }

        return ApiResponse(
            success=True,
            message="Meeting retrieved successfully",
            data=response_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/meetings/{meeting_id}", response_model=MeetingApiResponse)
def update_meeting_endpoint(
    updates: MeetingUpdate,
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a meeting"""
    try:
        meeting = get_meeting(db, meeting_id, current_user.id, raise_404=True)
        updated_meeting = update_meeting(db, meeting.id, updates, current_user.id)
        if not updated_meeting:
            raise HTTPException(status_code=400, detail="Failed to update meeting")

        response_data = {
            "id": updated_meeting.id,
            "title": updated_meeting.title,
            "description": updated_meeting.description,
            "url": updated_meeting.url,
            "start_time": updated_meeting.start_time,
            "created_by": updated_meeting.created_by,
            "is_personal": updated_meeting.is_personal,
            "status": updated_meeting.status,
            "is_deleted": updated_meeting.is_deleted,
            "created_at": updated_meeting.created_at,
            "updated_at": updated_meeting.updated_at,
            "projects": [],
            "can_access": True,
        }

        return ApiResponse(
            success=True,
            message="Meeting updated successfully",
            data=response_data,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/meetings/{meeting_id}", response_model=ApiResponse[dict])
def delete_meeting_endpoint(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a meeting"""
    try:
        meeting = get_meeting(db, meeting_id, current_user.id, raise_404=True)
        check_delete_permissions(db, meeting, current_user.id)
        success = delete_meeting(db, meeting.id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Meeting not found")

        return ApiResponse(
            success=True,
            message="Meeting deleted successfully",
            data={},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/projects/{project_id}/meetings/{meeting_id}", response_model=ApiResponse[dict])
def add_meeting_to_project_endpoint(
    project_id: uuid.UUID,
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add meeting to project"""
    try:
        success = add_meeting_to_project(db, meeting_id, project_id, current_user.id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add meeting to project")

        return ApiResponse(
            success=True,
            message="Meeting added to project successfully",
            data={},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/projects/{project_id}/meetings/{meeting_id}", response_model=ApiResponse[dict])
def remove_meeting_from_project_endpoint(
    project_id: uuid.UUID,
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove meeting from project"""
    try:
        success = remove_meeting_from_project(db, meeting_id, project_id, current_user.id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to remove meeting from project")

        return ApiResponse(
            success=True,
            message="Meeting removed from project successfully",
            data={},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/meetings/{meeting_id}/audio-files", response_model=ApiResponse[dict])
def upload_meeting_audio_endpoint(
    meeting_id: uuid.UUID,
    file: UploadFile = File(...),
    seq_order: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload an audio file to a meeting and enqueue ASR (mock) processing."""
    try:
        # Validate meeting and access control
        meeting = validate_meeting_for_audio_operations(db, meeting_id, current_user.id)

        # Validate file size and content type (≤ 100MB)
        content = file.file.read()
        size_bytes = len(content)
        if size_bytes > 100 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 100MB)")

        allowed_types = {
            "audio/mpeg",
            "audio/wav",
            "audio/mp3",
            "audio/mp4",
            "audio/x-m4a",
            "audio/m4a",
        }
        if file.content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Unsupported audio type")

        # Create and upload
        audio = create_audio_file(
            db,
            meeting_id=meeting_id,
            uploaded_by=current_user.id,
            filename=file.filename,
            content_type=file.content_type,
            file_bytes=content,
            seq_order=seq_order,
        )
        if not audio:
            raise HTTPException(status_code=400, detail="Failed to upload audio")

        # Enqueue Celery task (mock ASR)
        async_result = process_audio_task.delay(str(audio.id), str(current_user.id))

        return ApiResponse(
            success=True,
            message="Audio uploaded successfully",
            data={
                "audio_file_id": str(audio.id),
                "storage_url": audio.file_url,
                "task_id": async_result.id if async_result else None,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/meetings/{meeting_id}/audio-files",
    response_model=MeetingAudioFilesPaginatedResponse,
)
def list_meeting_audio_endpoint(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    try:
        # Validate meeting and access control
        meeting = validate_meeting_for_audio_operations(db, meeting_id, current_user.id)

        rows, total = get_meeting_audio_files(db, meeting_id, page, limit)

        pagination_meta = create_pagination_meta(page, limit, total)
        items = [
            AudioFileItem(
                id=r.id,
                file_url=r.file_url,
                seq_order=r.seq_order,
                duration_seconds=r.duration_seconds,
                uploaded_by=r.uploaded_by,
                created_at=r.created_at,
                can_access=True,
            )
            for r in rows
        ]

        return PaginatedResponse(
            success=True,
            message="Audio files retrieved successfully",
            data=items,
            pagination=pagination_meta,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
