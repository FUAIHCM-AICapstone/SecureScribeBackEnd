import uuid
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.meeting import Meeting, ProjectMeeting
from app.models.project import UserProject
from app.schemas.meeting import MeetingCreate, MeetingFilter, MeetingUpdate
from app.utils.meeting import (
    can_delete_meeting,
    check_meeting_access,
    notify_meeting_members,
    validate_meeting_url,
)


def create_meeting(
    db: Session, meeting_data: MeetingCreate, created_by: uuid.UUID
) -> Meeting:
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
            project_meeting = ProjectMeeting(
                project_id=project_id, meeting_id=meeting.id
            )
            db.add(project_meeting)
        db.commit()

    # Send notifications
    notify_meeting_members(db, meeting, "created", created_by)

    return meeting


def get_meeting(
    db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID
) -> Optional[Meeting]:
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
        return None

    if not check_meeting_access(db, meeting, user_id):
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
    query = (
        db.query(Meeting)
        .options(
            joinedload(Meeting.projects).joinedload(ProjectMeeting.project),
            joinedload(Meeting.created_by_user),
        )
        .filter(Meeting.is_deleted == False)
    )

    # Access control filter
    personal_meetings = (
        db.query(Meeting.id)
        .filter(Meeting.is_personal == True, Meeting.created_by == user_id)
        .subquery()
    )

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

    # Meetings with no linked projects (accessible to everyone)
    meetings_no_projects = (
        db.query(Meeting.id)
        .filter(Meeting.is_personal == False)
        .outerjoin(ProjectMeeting)
        .group_by(Meeting.id)
        .having(func.count(ProjectMeeting.project_id) == 0)
        .subquery()
    )

    query = query.filter(
        or_(
            Meeting.id.in_(personal_meetings),
            Meeting.id.in_(accessible_projects),
            Meeting.id.in_(meetings_no_projects),
        )
    )

    # Apply filters
    if filters:
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

        # Project filter
        if filters.project_id:
            query = query.join(ProjectMeeting).filter(
                ProjectMeeting.project_id == filters.project_id
            )

        # Tag filter
        if filters.tag_ids:
            from app.models.meeting import MeetingTag

            query = query.join(MeetingTag).filter(
                MeetingTag.tag_id.in_(filters.tag_ids)
            )

    # Additional filtering can be added here if needed

    total = query.count()
    meetings = query.offset((page - 1) * limit).limit(limit).all()

    return meetings, total


def update_meeting(
    db: Session, meeting_id: uuid.UUID, updates: MeetingUpdate, user_id: uuid.UUID
) -> Optional[Meeting]:
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
    """Soft delete meeting"""
    meeting = (
        db.query(Meeting)
        .filter(Meeting.id == meeting_id, Meeting.is_deleted == False)
        .first()
    )

    if not meeting or not can_delete_meeting(db, meeting, user_id):
        return False

    meeting.is_deleted = True
    db.commit()

    return True


def add_meeting_to_project(
    db: Session, meeting_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
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


def remove_meeting_from_project(
    db: Session, meeting_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
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
