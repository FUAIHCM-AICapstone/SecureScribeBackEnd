import uuid
from io import BytesIO
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.constants.messages import MessageDescriptions
from app.core.config import settings
from app.crud.meeting import (
    crud_check_project_exists,
    crud_create_audio_file,
    crud_create_meeting,
    crud_delete_audio_file,
    crud_get_meeting,
    crud_get_meeting_associated_files,
    crud_get_meeting_audio_files,
    crud_get_meetings,
    crud_get_next_audio_file_seq_order,
    crud_link_meeting_to_project,
    crud_soft_delete_meeting,
    crud_unlink_meeting_from_project,
    crud_update_audio_file_url,
    crud_update_meeting,
)
from app.events.domain_events import BaseDomainEvent, build_diff
from app.models.meeting import AudioFile, Meeting
from app.schemas.meeting import MeetingCreate, MeetingFilter, MeetingResponse, MeetingUpdate, MeetingWithProjects, ProjectResponse
from app.schemas.user import UserResponse
from app.services.event_manager import EventManager
from app.utils.meeting import (
    can_delete_meeting,
    check_meeting_access,
    notify_meeting_members,
    validate_meeting_url,
)
from app.utils.minio import delete_file_from_minio, generate_presigned_url, get_minio_client


def create_meeting(db: Session, meeting_data: MeetingCreate, created_by: uuid.UUID) -> Meeting:
    meeting = crud_create_meeting(
        db,
        title=meeting_data.title,
        description=meeting_data.description,
        url=meeting_data.url,
        start_time=meeting_data.start_time,
        is_personal=meeting_data.is_personal,
        created_by=created_by,
        status="active",
        is_deleted=False,
    )
    EventManager.emit_domain_event(
        BaseDomainEvent(
            event_name="meeting.created",
            actor_user_id=created_by,
            target_type="meeting",
            target_id=meeting.id,
            metadata={"title": meeting.title, "is_personal": meeting.is_personal},
        )
    )
    if not meeting_data.is_personal and meeting_data.project_ids:
        for project_id in meeting_data.project_ids:
            crud_link_meeting_to_project(db, meeting.id, project_id)
    notify_meeting_members(db, meeting, "created", created_by)
    return meeting


def get_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, raise_404: bool = False) -> Optional[Meeting]:
    meeting = crud_get_meeting(db, meeting_id)
    if not meeting:
        if raise_404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageDescriptions.MEETING_ACCESS_DENIED)
        return None
    if not check_meeting_access(db, meeting, user_id):
        if raise_404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageDescriptions.MEETING_ACCESS_DENIED)
        return None
    return meeting


def get_meeting_by_url(db: Session, meeting_url: str) -> Optional[Meeting]:
    """Get meeting by URL"""
    return db.query(Meeting).filter(Meeting.url == meeting_url).first()


def get_meetings(db: Session, user_id: uuid.UUID, filters: Optional[MeetingFilter] = None, page: int = 1, limit: int = 20) -> Tuple[List[Meeting], int]:
    filter_params = {}
    if filters:
        filter_params = {
            "title": filters.title,
            "description": filters.description,
            "status": filters.status,
            "is_personal": filters.is_personal,
            "created_by": filters.created_by,
            "start_time_gte": filters.start_time_gte,
            "start_time_lte": filters.start_time_lte,
            "project_id": filters.project_id,
            "tag_ids": filters.tag_ids,
        }
    return crud_get_meetings(db, user_id, page=page, limit=limit, **filter_params)


def update_meeting(db: Session, meeting_id: uuid.UUID, updates: MeetingUpdate, user_id: uuid.UUID) -> Optional[Meeting]:
    meeting = get_meeting(db, meeting_id, user_id)
    if not meeting:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting.update_failed",
                actor_user_id=user_id,
                target_type="meeting",
                target_id=meeting_id,
                metadata={"reason": "not_found"},
            )
        )
        return None
    if updates.url and not validate_meeting_url(updates.url):
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting.update_failed",
                actor_user_id=user_id,
                target_type="meeting",
                target_id=meeting_id,
                metadata={"reason": "invalid_url", "url": updates.url},
            )
        )
        return None
    update_data = updates.model_dump(exclude_unset=True)
    original = {k: getattr(meeting, k, None) for k in update_data.keys()}
    meeting = crud_update_meeting(db, meeting_id, **update_data)
    diff = build_diff(original, {k: getattr(meeting, k, None) for k in update_data.keys()})
    if diff:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting.updated",
                actor_user_id=user_id,
                target_type="meeting",
                target_id=meeting.id,
                metadata={"diff": diff},
            )
        )
    notify_meeting_members(db, meeting, "updated", user_id)
    return meeting


def delete_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    meeting = get_meeting(db, meeting_id, user_id)
    if not meeting:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting.delete_failed",
                actor_user_id=user_id,
                target_type="meeting",
                target_id=meeting_id,
                metadata={"reason": "not_found"},
            )
        )
        return False
    if not can_delete_meeting(db, meeting, user_id):
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting.delete_failed",
                actor_user_id=user_id,
                target_type="meeting",
                target_id=meeting_id,
                metadata={"reason": "permission_denied"},
            )
        )
        return False
    associated_files = crud_get_meeting_associated_files(db, meeting_id)
    for file in associated_files:
        delete_file_from_minio(settings.MINIO_BUCKET_NAME, str(file.id))
        db.delete(file)
    crud_soft_delete_meeting(db, meeting_id)
    EventManager.emit_domain_event(
        BaseDomainEvent(
            event_name="meeting.deleted",
            actor_user_id=user_id,
            target_type="meeting",
            target_id=meeting_id,
            metadata={},
        )
    )
    return True


def add_meeting_to_project(db: Session, meeting_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    meeting = get_meeting(db, meeting_id, user_id)
    if not meeting:
        return False
    if not crud_check_project_exists(db, project_id):
        return False
    meeting.is_personal = False
    db.commit()
    return crud_link_meeting_to_project(db, meeting_id, project_id)


def remove_meeting_from_project(db: Session, meeting_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    meeting = get_meeting(db, meeting_id, user_id)
    if not meeting:
        return False
    if not crud_check_project_exists(db, project_id):
        return False
    return crud_unlink_meeting_from_project(db, meeting_id, project_id)


def validate_meeting_for_audio_operations(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Meeting:
    meeting = crud_get_meeting(db, meeting_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageDescriptions.MEETING_NOT_FOUND)
    if not check_meeting_access(db, meeting, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MessageDescriptions.ACCESS_DENIED)
    return meeting


def check_delete_permissions(db: Session, meeting: Meeting, current_user_id: uuid.UUID) -> Meeting:
    if not can_delete_meeting(db, meeting, current_user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=MessageDescriptions.MEETING_UNAUTHORIZED_DELETE)
    return meeting


def create_audio_file(
    db: Session,
    meeting_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    filename: str,
    content_type: str,
    file_bytes: bytes,
    seq_order: Optional[int] = None,
) -> Optional[AudioFile]:
    seq = seq_order if seq_order is not None else crud_get_next_audio_file_seq_order(db, meeting_id)
    audio = crud_create_audio_file(db, meeting_id, uploaded_by, seq)
    ext = ""
    if "." in filename:
        ext = filename.split(".")[-1].lower()
    object_name = f"meetings/{meeting_id}/audio/{audio.id}{('.' + ext) if ext else ''}"
    try:
        client = get_minio_client()
        file_data = BytesIO(file_bytes)
        client.put_object(
            bucket_name=settings.MINIO_BUCKET_NAME,
            object_name=object_name,
            data=file_data,
            length=len(file_bytes),
            content_type=content_type,
        )
        url = generate_presigned_url(settings.MINIO_BUCKET_NAME, object_name)
        crud_update_audio_file_url(db, audio.id, url)
        return crud_get_meeting(db, meeting_id)
    except Exception:
        try:
            crud_delete_audio_file(db, audio.id)
        except Exception:
            pass
        return None


def get_meeting_audio_files(db: Session, meeting_id: uuid.UUID, page: int = 1, limit: int = 20) -> Tuple[List[AudioFile], int]:
    return crud_get_meeting_audio_files(db, meeting_id, page=page, limit=limit)


def serialize_meeting(meeting: Meeting) -> MeetingResponse:
    creator = UserResponse.model_validate(meeting.created_by_user, from_attributes=True) if getattr(meeting, "created_by_user", None) else None
    projects = []
    if hasattr(meeting, "projects") and meeting.projects:
        projects = [ProjectResponse.model_validate(project_meeting.project, from_attributes=True) for project_meeting in meeting.projects if project_meeting.project]
    return MeetingResponse(
        id=meeting.id,
        title=meeting.title,
        description=meeting.description,
        url=meeting.url,
        start_time=meeting.start_time,
        created_by=meeting.created_by,
        is_personal=meeting.is_personal,
        status=meeting.status,
        is_deleted=meeting.is_deleted,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
        projects=projects,
        creator=creator,
        can_access=True,
    )


def serialize_meeting_with_projects(meeting: Meeting, project_count: int = 0, member_count: int = 0, meeting_note=None, transcripts=None) -> MeetingWithProjects:
    creator = UserResponse.model_validate(meeting.created_by_user, from_attributes=True) if getattr(meeting, "created_by_user", None) else None
    projects = []
    if hasattr(meeting, "projects") and meeting.projects:
        projects = [ProjectResponse.model_validate(project_meeting.project, from_attributes=True) for project_meeting in meeting.projects if project_meeting.project]
    return MeetingWithProjects(
        id=meeting.id,
        title=meeting.title,
        description=meeting.description,
        url=meeting.url,
        start_time=meeting.start_time,
        created_by=meeting.created_by,
        is_personal=meeting.is_personal,
        status=meeting.status,
        is_deleted=meeting.is_deleted,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
        projects=projects,
        creator=creator,
        can_access=True,
        project_count=project_count,
        member_count=member_count,
        meeting_note=meeting_note,
        transcripts=transcripts or [],
    )
