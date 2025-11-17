import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.events.domain_events import BaseDomainEvent, build_diff
from app.models.meeting import AudioFile, Meeting, ProjectMeeting
from app.models.project import UserProject
from app.schemas.meeting import MeetingCreate, MeetingFilter, MeetingResponse, MeetingUpdate, MeetingWithProjects, ProjectResponse
from app.schemas.user import UserResponse
from app.services.event_manager import EventManager
from app.utils.meeting import (
    can_delete_meeting,
    check_meeting_access,
    notify_meeting_members,
    validate_meeting_url,
)
from app.utils.minio import generate_presigned_url, get_minio_client


def create_meeting(db: Session, meeting_data: MeetingCreate, created_by: uuid.UUID) -> Meeting:
    """Create new meeting"""
    meeting = Meeting(
        title=meeting_data.title,
        description=meeting_data.description,
        url=meeting_data.url,
        start_time=meeting_data.start_time,
        is_personal=meeting_data.is_personal,
        created_by=created_by,
        status="active",  # Set default status explicitly
        is_deleted=False,  # Set default is_deleted explicitly
    )

    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    # Emit domain event for creation
    EventManager.emit_domain_event(
        BaseDomainEvent(
            event_name="meeting.created",
            actor_user_id=created_by,
            target_type="meeting",
            target_id=meeting.id,
            metadata={"title": meeting.title, "is_personal": meeting.is_personal},
        )
    )

    # Link to projects if not personal
    if not meeting_data.is_personal and meeting_data.project_ids:
        for project_id in meeting_data.project_ids:
            project_meeting = ProjectMeeting(project_id=project_id, meeting_id=meeting.id)
            db.add(project_meeting)
        db.commit()

    # Send notifications
    notify_meeting_members(db, meeting, "created", created_by)

    return meeting


def get_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, raise_404: bool = False) -> Optional[Meeting]:
    """Get meeting by ID with access control"""
    meeting = (
        db.query(Meeting)
        .options(
            joinedload(Meeting.projects).joinedload(ProjectMeeting.project),
            joinedload(Meeting.created_by_user),
        )
        .filter(Meeting.id == meeting_id, Meeting.is_deleted == False)
        .first()
    )

    if not meeting:
        if raise_404:
            raise HTTPException(status_code=404, detail="Meeting not found or access denied")
        return None

    if not check_meeting_access(db, meeting, user_id):
        if raise_404:
            raise HTTPException(status_code=404, detail="Meeting not found or access denied")
        return None

    return meeting


def _personal_meetings_subquery(db: Session, user_id: uuid.UUID):
    return db.query(Meeting.id).filter(Meeting.is_personal == True, Meeting.created_by == user_id).subquery()


def _accessible_projects_subquery(db: Session, user_id: uuid.UUID):
    return (
        db.query(ProjectMeeting.meeting_id)
        .join(
            UserProject,
            and_(
                UserProject.project_id == ProjectMeeting.project_id,
                UserProject.user_id == user_id,
            ),
        )
        .subquery()
    )


def _meetings_no_projects_subquery(db: Session):
    return db.query(Meeting.id).filter(Meeting.is_personal == False).outerjoin(ProjectMeeting).group_by(Meeting.id).having(func.count(ProjectMeeting.project_id) == 0).subquery()


def _apply_filters(db: Session, query, filters: Optional[MeetingFilter], user_id: uuid.UUID):
    if not filters:
        print("\033[93m⏭️ No additional filters to apply\033[0m")
        return query

    if filters.title:
        query = query.filter(Meeting.title.ilike(f"%{filters.title}%"))
    if filters.description:
        query = query.filter(Meeting.description.ilike(f"%{filters.description}%"))
    if filters.status:
        query = query.filter(Meeting.status == filters.status)
    if filters.is_personal is not None:
        query = query.filter(Meeting.is_personal == filters.is_personal)
    if filters.created_by:
        query = query.filter(Meeting.created_by == filters.created_by)
    if filters.start_time_gte:
        query = query.filter(Meeting.start_time >= filters.start_time_gte)
    if filters.start_time_lte:
        query = query.filter(Meeting.start_time <= filters.start_time_lte)

    if filters.project_id:
        user_is_member = db.query(UserProject).filter(UserProject.user_id == user_id, UserProject.project_id == filters.project_id).first() is not None
        if not user_is_member:
            return query.filter(False)
        return query.join(ProjectMeeting).filter(ProjectMeeting.project_id == filters.project_id)

    if filters.tag_ids:
        from app.models.meeting import MeetingTag

        query = query.join(MeetingTag).filter(MeetingTag.tag_id.in_(filters.tag_ids))
    return query


def get_meetings(
    db: Session,
    user_id: uuid.UUID,
    filters: Optional[MeetingFilter] = None,
    page: int = 1,
    limit: int = 20,
) -> Tuple[List[Meeting], int]:
    """Get meetings with filtering and pagination"""

    base_query = (
        db.query(Meeting)
        .options(
            joinedload(Meeting.projects).joinedload(ProjectMeeting.project),
            joinedload(Meeting.created_by_user),
        )
        .filter(Meeting.is_deleted == False)
    )

    personal_meetings = _personal_meetings_subquery(db, user_id)
    accessible_projects = _accessible_projects_subquery(db, user_id)
    meetings_no_projects = _meetings_no_projects_subquery(db)

    query = base_query.filter(
        or_(
            Meeting.id.in_(personal_meetings),
            Meeting.id.in_(accessible_projects),
            Meeting.id.in_(meetings_no_projects),
        )
    )

    query = _apply_filters(db, query, filters, user_id)

    print("\033[96m🔢 Executing count query...\033[0m")
    total = query.count()

    meetings = query.offset((page - 1) * limit).limit(limit).all()
    return meetings, total


def update_meeting(db: Session, meeting_id: uuid.UUID, updates: MeetingUpdate, user_id: uuid.UUID) -> Optional[Meeting]:
    """Update meeting"""
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

    # Validate URL if provided
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

    # Update fields
    update_data = updates.model_dump(exclude_unset=True)
    original = {k: getattr(meeting, k, None) for k in update_data.keys()}
    for field, value in update_data.items():
        setattr(meeting, field, value)

    meeting.updated_at = None  # Will be set by database trigger
    db.commit()
    db.refresh(meeting)

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

    # Send notifications
    notify_meeting_members(db, meeting, "updated", user_id)

    return meeting


def delete_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Soft delete meeting and hard delete associated files"""
    # Validate user has access to the meeting
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

    # Check if user has permission to delete this meeting
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

    # Get all files associated with this meeting
    from app.core.config import settings
    from app.models.file import File
    from app.utils.minio import delete_file_from_minio

    associated_files = db.query(File).filter(File.meeting_id == meeting_id).all()

    # Delete files from MinIO storage and database
    for file in associated_files:
        # Delete from MinIO storage
        delete_file_from_minio(settings.MINIO_BUCKET_NAME, str(file.id))

        # Delete from database
        db.delete(file)

    # Soft delete the meeting
    meeting.is_deleted = True
    db.commit()

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
    """Add meeting to project"""
    meeting = get_meeting(db, meeting_id, user_id)
    if not meeting:
        return False

    # Check if already linked
    existing = (
        db.query(ProjectMeeting)
        .filter(
            ProjectMeeting.meeting_id == meeting_id,
            ProjectMeeting.project_id == project_id,
        )
        .first()
    )

    if existing:
        return True

    # When adding to a project, meeting is no longer personal
    meeting.is_personal = False
    meeting.updated_at = None  # Will be set by database trigger

    project_meeting = ProjectMeeting(project_id=project_id, meeting_id=meeting_id)
    db.add(project_meeting)
    db.commit()

    return True


def remove_meeting_from_project(db: Session, meeting_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Remove meeting from project"""
    meeting = get_meeting(db, meeting_id, user_id)
    if not meeting:
        return False

    project_meeting = (
        db.query(ProjectMeeting)
        .filter(
            ProjectMeeting.meeting_id == meeting_id,
            ProjectMeeting.project_id == project_id,
        )
        .first()
    )

    if not project_meeting:
        return False

    db.delete(project_meeting)
    db.commit()

    return True


def validate_meeting_for_audio_operations(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Meeting:
    """Validate meeting exists and user has access for audio operations"""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.is_deleted == False).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not check_meeting_access(db, meeting, user_id):
        raise HTTPException(status_code=403, detail="Access denied")

    return meeting


def check_delete_permissions(db: Session, meeting: Meeting, current_user_id: uuid.UUID) -> Meeting:
    """Check if user can delete meeting and raise HTTPException if not"""
    if not can_delete_meeting(db, meeting, current_user_id):
        raise HTTPException(status_code=403, detail="You don't have permission to delete this meeting")
    return meeting


def _get_next_seq_order(db: Session, meeting_id: uuid.UUID) -> int:
    last = db.query(AudioFile).filter(AudioFile.meeting_id == meeting_id, AudioFile.is_deleted == False).order_by(AudioFile.seq_order.desc().nullslast(), AudioFile.created_at.desc()).first()
    if not last or last.seq_order is None:
        return 1
    return int(last.seq_order) + 1


def create_audio_file(
    db: Session,
    meeting_id: uuid.UUID,
    uploaded_by: uuid.UUID,
    filename: str,
    content_type: str,
    file_bytes: bytes,
    seq_order: Optional[int] = None,
) -> Optional[AudioFile]:
    """Create AudioFile row and upload bytes to MinIO, then set file_url."""
    # Create DB row first
    audio = AudioFile(
        meeting_id=meeting_id,
        uploaded_by=uploaded_by,
        seq_order=seq_order if seq_order is not None else _get_next_seq_order(db, meeting_id),
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)

    # Determine extension
    ext = ""
    if "." in filename:
        ext = filename.split(".")[-1].lower()

    object_name = f"meetings/{meeting_id}/audio/{audio.id}{('.' + ext) if ext else ''}"

    try:
        client = get_minio_client()
        from io import BytesIO

        file_data = BytesIO(file_bytes)
        client.put_object(
            bucket_name=settings.MINIO_BUCKET_NAME,
            object_name=object_name,
            data=file_data,
            length=len(file_bytes),
            content_type=content_type,
        )

        url = generate_presigned_url(settings.MINIO_BUCKET_NAME, object_name)
        audio.file_url = url
        db.commit()
        db.refresh(audio)
        return audio
    except Exception:
        # Rollback DB row if upload failed
        try:
            db.delete(audio)
            db.commit()
        except Exception:
            pass
        return None


def get_meeting_audio_files(db: Session, meeting_id: uuid.UUID, page: int = 1, limit: int = 20) -> Tuple[List[AudioFile], int]:
    q = db.query(AudioFile).filter(AudioFile.meeting_id == meeting_id, AudioFile.is_deleted == False)
    # Order by seq_order ASC (NULLS LAST), then created_at ASC
    q = q.order_by(AudioFile.seq_order.asc().nullslast(), AudioFile.created_at.asc())
    total = q.count()
    rows = q.offset((page - 1) * limit).limit(limit).all()
    return rows, total


def serialize_meeting(meeting: Meeting) -> MeetingResponse:
    """Map a Meeting ORM object to MeetingResponse with expanded creator information.

    Ensures creator is a full UserResponse object and projects are properly formatted.
    """
    creator = UserResponse.model_validate(meeting.created_by_user, from_attributes=True) if getattr(meeting, "created_by_user", None) else None

    # Map projects from ProjectMeeting relationships to ProjectResponse objects
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
    """Map a Meeting ORM object to MeetingWithProjects with expanded information.

    Includes additional fields like project_count, member_count, meeting_note, and transcripts.
    """
    creator = UserResponse.model_validate(meeting.created_by_user, from_attributes=True) if getattr(meeting, "created_by_user", None) else None

    # Map projects from ProjectMeeting relationships to ProjectResponse objects
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
