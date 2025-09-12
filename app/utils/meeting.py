import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.models.project import UserProject
from app.models.user import User  # noqa: F401
from app.schemas.notification import NotificationCreate
from app.services.notification import create_notifications_bulk


def validate_meeting_url(url: Optional[str]) -> bool:
    """#TODO: Implement URL validation logic"""
    if not url:
        return True
    # Basic URL validation placeholder
    return url.startswith(("http://", "https://"))


def check_meeting_access(db: Session, meeting: Meeting, user_id: uuid.UUID) -> bool:
    """Check if user can access meeting"""
    if meeting.is_personal:
        return meeting.created_by == user_id
    else:
        # Check if user is member of any linked projects
        linked_projects = get_meeting_projects(db, meeting.id)

        # If meeting has linked projects, user must be member of at least one
        if linked_projects:
            for project_id in linked_projects:
                user_project = (
                    db.query(UserProject)
                    .filter(
                        UserProject.user_id == user_id,
                        UserProject.project_id == project_id,
                    )
                    .first()
                )
                if user_project:
                    return True
            return False
        else:
            # If meeting has no linked projects, everyone can access
            return True


def get_meeting_projects(db: Session, meeting_id: uuid.UUID) -> List[uuid.UUID]:
    """Get list of project IDs linked to meeting"""
    from app.models.meeting import ProjectMeeting

    project_meetings = (
        db.query(ProjectMeeting).filter(ProjectMeeting.meeting_id == meeting_id).all()
    )
    return [pm.project_id for pm in project_meetings]


def can_delete_meeting(db: Session, meeting: Meeting, user_id: uuid.UUID) -> bool:
    """Check if user can delete meeting"""
    # Owner of meeting can delete
    if meeting.created_by == user_id:
        return True

    # Owner/admin of linked projects can delete
    linked_projects = get_meeting_projects(db, meeting.id)
    for project_id in linked_projects:
        user_project = (
            db.query(UserProject)
            .filter(
                UserProject.user_id == user_id,
                UserProject.project_id == project_id,
                UserProject.role.in_(["admin", "owner"]),
            )
            .first()
        )
        if user_project:
            return True

    return False


def notify_meeting_members(
    db: Session, meeting: Meeting, action: str, user_id: uuid.UUID
):
    """Send notifications to meeting members"""
    try:
        linked_projects = get_meeting_projects(db, meeting.id)

        # Get all users from linked projects
        member_ids = []
        for project_id in linked_projects:
            user_projects = (
                db.query(UserProject).filter(UserProject.project_id == project_id).all()
            )
            member_ids.extend([up.user_id for up in user_projects])

        # Remove duplicates and current user
        member_ids = list(set(member_ids) - {user_id})

        if member_ids:
            notification_data = NotificationCreate(
                user_ids=member_ids,
                type=f"meeting.{action}",
                payload={
                    "meeting_id": str(meeting.id),
                    "meeting_title": meeting.title or "Untitled Meeting",
                    "action": action,
                    "actor_id": str(user_id),
                },
                channel="in_app",
            )
            create_notifications_bulk(
                db,
                notification_data.user_ids,
                type=notification_data.type,
                payload=notification_data.payload,
                channel=notification_data.channel,
            )
    except Exception:
        pass  # Silent fail for notifications
