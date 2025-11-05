import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.meeting import AudioFile, Meeting, ProjectMeeting
from app.models.project import UserProject
from app.schemas.meeting import MeetingCreate, MeetingFilter, MeetingResponse, MeetingUpdate
from app.schemas.user import UserResponse
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


def get_meetings(
    db: Session,
    user_id: uuid.UUID,
    filters: Optional[MeetingFilter] = None,
    page: int = 1,
    limit: int = 20,
) -> Tuple[List[Meeting], int]:
    """Get meetings with filtering and pagination"""
    print("\033[96m🌟 [GET_MEETINGS] Function called\033[0m")
    print(f"\033[94m👤 User ID: {user_id}\033[0m")
    print(f"\033[95m🔍 Filters: {filters}\033[0m")
    print(f"\033[93m📄 Page: {page}, Limit: {limit}\033[0m")

    print("\033[92m🏗️ Building base query...\033[0m")
    query = (
        db.query(Meeting)
        .options(
            joinedload(Meeting.projects).joinedload(ProjectMeeting.project),
            joinedload(Meeting.created_by_user),
        )
        .filter(Meeting.is_deleted == False)
    )
    print("\033[92m✅ Base query built with joined loads\033[0m")

    print("\033[95m🔐 Applying access control filters...\033[0m")
    print(f"\033[94m👥 Getting personal meetings for user {user_id}...\033[0m")
    personal_meetings = db.query(Meeting.id).filter(Meeting.is_personal == True, Meeting.created_by == user_id).subquery()
    print("\033[94m✅ Personal meetings subquery created\033[0m")

    print(f"\033[95m🏢 Getting accessible projects for user {user_id}...\033[0m")
    accessible_projects = (
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
    print("\033[95m✅ Accessible projects subquery created\033[0m")

    print("\033[96m🌍 Getting public meetings (no linked projects)...\033[0m")
    meetings_no_projects = db.query(Meeting.id).filter(Meeting.is_personal == False).outerjoin(ProjectMeeting).group_by(Meeting.id).having(func.count(ProjectMeeting.project_id) == 0).subquery()
    print("\033[96m✅ Public meetings subquery created\033[0m")

    print("\033[92m🔗 Combining access control filters...\033[0m")
    query = query.filter(
        or_(
            Meeting.id.in_(personal_meetings),
            Meeting.id.in_(accessible_projects),
            Meeting.id.in_(meetings_no_projects),
        )
    )
    print("\033[92m✅ Access control filters applied\033[0m")

    # Apply filters
    if filters:
        print("\033[93m🎯 Applying additional filters...\033[0m")
        if filters.title:
            print(f"\033[95m📝 Filtering by title: '{filters.title}'\033[0m")
            query = query.filter(Meeting.title.ilike(f"%{filters.title}%"))
        if filters.description:
            print(f"\033[95m📝 Filtering by description: '{filters.description}'\033[0m")
            query = query.filter(Meeting.description.ilike(f"%{filters.description}%"))
        if filters.status:
            print(f"\033[93m📊 Filtering by status: '{filters.status}'\033[0m")
            query = query.filter(Meeting.status == filters.status)
        if filters.is_personal is not None:
            print(f"\033[94m👤 Filtering by is_personal: {filters.is_personal}\033[0m")
            query = query.filter(Meeting.is_personal == filters.is_personal)
        if filters.created_by:
            print(f"\033[91m👨‍💼 Filtering by created_by: {filters.created_by}\033[0m")
            query = query.filter(Meeting.created_by == filters.created_by)
        if filters.start_time_gte:
            print(f"\033[92m📅 Filtering by start_time >= {filters.start_time_gte}\033[0m")
            query = query.filter(Meeting.start_time >= filters.start_time_gte)
        if filters.start_time_lte:
            print(f"\033[92m📅 Filtering by start_time <= {filters.start_time_lte}\033[0m")
            query = query.filter(Meeting.start_time <= filters.start_time_lte)

        if filters.project_id:
            print(f"\033[95m🏢 Applying project filter: {filters.project_id}\033[0m")
            user_is_member = db.query(UserProject).filter(
                UserProject.user_id == user_id,
                UserProject.project_id == filters.project_id
            ).first() is not None

            if not user_is_member:
                print(f"\033[91m❌ User is not member of project {filters.project_id}, returning empty result\033[0m")
                query = query.filter(False)
            else:
                print(f"\033[92m✅ User is member of project {filters.project_id}, joining with ProjectMeeting\033[0m")
                query = query.join(ProjectMeeting).filter(ProjectMeeting.project_id == filters.project_id)

        if filters.tag_ids:
            print(f"\033[96m🏷️ Applying tag filter: {filters.tag_ids}\033[0m")
            from app.models.meeting import MeetingTag
            query = query.join(MeetingTag).filter(MeetingTag.tag_id.in_(filters.tag_ids))
        print("\033[93m✅ All filters applied\033[0m")
    else:
        print("\033[93m⏭️ No additional filters to apply\033[0m")

    print("\033[96m🔢 Executing count query...\033[0m")
    total = query.count()
    print(f"\033[96m📊 Total meetings found: {total}\033[0m")

    print(f"\033[92m📋 Executing main query (offset: {(page - 1) * limit}, limit: {limit})...\033[0m")
    meetings = query.offset((page - 1) * limit).limit(limit).all()
    print(f"\033[92m📦 Retrieved {len(meetings)} meetings\033[0m")

    if meetings:
        print("\033[94m📝 Meeting details:\033[0m")
        for i, meeting in enumerate(meetings[:5]):  # Show first 5 meetings
            print(f"\033[94m  {i+1}. ID: {meeting.id}, Title: '{meeting.title}', Personal: {meeting.is_personal}\033[0m")
        if len(meetings) > 5:
            print(f"\033[94m  ... and {len(meetings) - 5} more meetings\033[0m")

    print("\033[92m🎉 Function completed successfully!\033[0m")
    return meetings, total


def update_meeting(db: Session, meeting_id: uuid.UUID, updates: MeetingUpdate, user_id: uuid.UUID) -> Optional[Meeting]:
    """Update meeting"""
    meeting = get_meeting(db, meeting_id, user_id)
    if not meeting:
        return None

    # Validate URL if provided
    if updates.url and not validate_meeting_url(updates.url):
        return None

    # Update fields
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(meeting, field, value)

    meeting.updated_at = None  # Will be set by database trigger
    db.commit()
    db.refresh(meeting)

    # Send notifications
    notify_meeting_members(db, meeting, "updated", user_id)

    return meeting


def delete_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """Soft delete meeting and hard delete associated files"""
    # Validate user has access to the meeting
    meeting = get_meeting(db, meeting_id, user_id)
    if not meeting:
        return False

    # Check if user has permission to delete this meeting
    if not can_delete_meeting(db, meeting, user_id):
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
    last = db.query(AudioFile).filter(AudioFile.meeting_id == meeting_id).order_by(AudioFile.seq_order.desc().nullslast(), AudioFile.created_at.desc()).first()
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
    q = db.query(AudioFile).filter(AudioFile.meeting_id == meeting_id)
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
        projects=[],
        creator=creator,
        can_access=True,
    )
