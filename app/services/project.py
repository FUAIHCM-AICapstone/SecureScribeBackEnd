import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.events.domain_events import BaseDomainEvent, build_diff
from app.models.file import File
from app.models.meeting import Meeting, ProjectMeeting
from app.models.project import Project, UserProject
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectFilter,
    ProjectResponse,
    ProjectUpdate,
    ProjectWithMembers,
    UserProjectCreate,
    UserProjectResponse,
)
from app.services.event_manager import EventManager
from app.utils.minio import delete_file_from_minio


def create_project(db: Session, project_data: ProjectCreate, created_by: uuid.UUID) -> Project:
    """
    Create a new project
    """
    project = Project(
        name=project_data.name,
        description=project_data.description,
        created_by=created_by,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    # Emit domain event (async audit)
    EventManager.emit_domain_event(
        BaseDomainEvent(
            event_name="project.created",
            actor_user_id=created_by,
            target_type="project",
            target_id=project.id,
            metadata={"name": project.name},
        )
    )

    # Add creator as project owner directly
    creator_user_project = UserProject(
        user_id=created_by,
        project_id=project.id,
        role="owner",
    )
    db.add(creator_user_project)
    db.commit()
    db.refresh(creator_user_project)

    return project


def get_project(db: Session, project_id: uuid.UUID, include_members: bool = False) -> Optional[Project]:
    """
    Get a project by ID
    """
    if include_members:
        return (
            db.query(Project)
            .options(
                joinedload(Project.users).joinedload(UserProject.user),
                joinedload(Project.created_by_user),
            )
            .filter(Project.id == project_id)
            .first()
        )
    else:
        return db.query(Project).filter(Project.id == project_id).first()


def get_projects(
    db: Session,
    filters: Optional[ProjectFilter] = None,
    page: int = 1,
    limit: int = 20,
    order_by: str = "created_at",
    dir: str = "desc",
) -> tuple[List[Project], int]:
    """
    Get projects with filtering and pagination
    """
    query = db.query(Project)

    # Apply filters
    if filters:
        if filters.name:
            query = query.filter(Project.name.ilike(f"%{filters.name}%"))
        if filters.is_archived is not None:
            query = query.filter(Project.is_archived == filters.is_archived)
        if filters.created_by:
            query = query.filter(Project.created_by == filters.created_by)
        if filters.created_at_gte:
            query = query.filter(Project.created_at >= filters.created_at_gte)
        if filters.created_at_lte:
            query = query.filter(Project.created_at <= filters.created_at_lte)

        # Filter by member
        if filters.member_id:
            query = query.join(UserProject).filter(UserProject.user_id == filters.member_id)

    # Apply ordering
    if hasattr(Project, order_by):
        order_column = getattr(Project, order_by)
        if dir.lower() == "desc":
            query = query.order_by(order_column.desc())
        else:
            query = query.order_by(order_column.asc())

    # Get total count
    total = query.count()

    # Apply pagination
    projects = query.offset((page - 1) * limit).limit(limit).all()

    return projects, total


def update_project(db: Session, project_id: uuid.UUID, updates: ProjectUpdate, actor_user_id: uuid.UUID | None = None) -> Optional[Project]:
    """
    Update a project
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        # Audit failure: not found
        if actor_user_id:
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="project.update_failed",
                    actor_user_id=actor_user_id,
                    target_type="project",
                    target_id=project_id,
                    metadata={"reason": "not_found", "detail": "Project not found"},
                )
            )
        return None

    update_data = updates.model_dump(exclude_unset=True)
    # Capture original values for diff
    original: Dict[str, Any] = {k: getattr(project, k, None) for k in update_data.keys()}
    for key, value in update_data.items():
        setattr(project, key, value)

    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)

    # Emit domain event with diff
    try:
        if actor_user_id:
            diff = build_diff(original, {k: getattr(project, k, None) for k in update_data.keys()})
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="project.updated",
                    actor_user_id=actor_user_id,
                    target_type="project",
                    target_id=project.id,
                    metadata={"diff": diff},
                )
            )
    except Exception as _:
        pass

    return project


def delete_project(db: Session, project_id: uuid.UUID, actor_user_id: uuid.UUID | None = None) -> bool:
    """
    Delete a project with proper cascade handling including meetings and files
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        if actor_user_id:
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="project.delete_failed",
                    actor_user_id=actor_user_id,
                    target_type="project",
                    target_id=project_id,
                    metadata={"reason": "not_found", "detail": "Project not found"},
                )
            )
        return False

    try:
        # Delete in correct order to avoid foreign key conflicts

        project_files = (
            db.query(File)
            .filter(
                File.project_id == project_id,
                File.meeting_id.is_(None),  # Only files directly associated with project
            )
            .all()
        )

        for file in project_files:
            # Delete from MinIO storage
            delete_file_from_minio(settings.MINIO_BUCKET_NAME, str(file.id))
            # Delete from database
            db.delete(file)

        # 2. Delete meetings associated with project and their files

        # Get all meeting IDs associated with this project
        project_meetings = db.query(ProjectMeeting).filter(ProjectMeeting.project_id == project_id).all()

        for project_meeting in project_meetings:
            # Delete files associated with this meeting
            meeting_files = db.query(File).filter(File.meeting_id == project_meeting.meeting_id).all()

            for file in meeting_files:
                # Delete from MinIO storage
                delete_file_from_minio(settings.MINIO_BUCKET_NAME, str(file.id))
                # Delete from database
                db.delete(file)

            # Soft delete the meeting
            meeting = db.query(Meeting).filter(Meeting.id == project_meeting.meeting_id).first()
            if meeting:
                meeting.is_deleted = True

        # 3. Delete ProjectMeeting relationships (projects_meetings table)
        db.query(ProjectMeeting).filter(ProjectMeeting.project_id == project_id).delete()

        # 4. Delete UserProject relationships (users_projects table)
        db.query(UserProject).filter(UserProject.project_id == project_id).delete()

        # 5. Delete TaskProject relationships (tasks_projects table)
        from app.models.task import TaskProject

        db.query(TaskProject).filter(TaskProject.project_id == project_id).delete()

        # 7. Finally delete the project
        db.delete(project)
        db.commit()
        # Emit domain event
        if actor_user_id:
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="project.deleted",
                    actor_user_id=actor_user_id,
                    target_type="project",
                    target_id=project_id,
                    metadata={},
                )
            )
        return True

    except Exception as e:
        db.rollback()
        print(f"Error deleting project {project_id}: {e}")
        return False


# User-Project relationship management
def add_user_to_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, role: str = "member", added_by_user_id: uuid.UUID = None) -> Optional[UserProject]:
    """
    Add a user to a project
    """
    # Check if user is already in project
    existing = db.query(UserProject).filter(and_(UserProject.project_id == project_id, UserProject.user_id == user_id)).first()

    if existing:
        return existing

    # Check if project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return None

    # Check if user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Emit failure event
        if added_by_user_id:
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="project.member_add_failed",
                    actor_user_id=added_by_user_id,
                    target_type="project",
                    target_id=project_id,
                    metadata={"reason": "not_found", "detail": "User not found", "user_id": str(user_id)},
                )
            )
        return None

    user_project = UserProject(
        user_id=user_id,
        project_id=project_id,
        role=role,
    )
    db.add(user_project)
    db.commit()
    db.refresh(user_project)

    if added_by_user_id:
        from app.events.project_events import UserAddedToProjectEvent

        event = UserAddedToProjectEvent(
            project_id=project_id,
            user_id=user_id,
            added_by_user_id=added_by_user_id,
            db=db,
        )
        EventManager.emit(event)

        # Emit domain event for audit
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="project.member_added",
                actor_user_id=added_by_user_id,
                target_type="project",
                target_id=project_id,
                metadata={"added_user_id": str(user_id), "role": role},
            )
        )

    return user_project


def remove_user_from_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID, removed_by_user_id: uuid.UUID = None, is_self_removal: bool = False) -> bool:
    """
    Remove a user from a project
    """
    user_project = db.query(UserProject).filter(and_(UserProject.project_id == project_id, UserProject.user_id == user_id)).first()

    if not user_project:
        # Emit failure event if member not found in project
        if removed_by_user_id:
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="project.member_remove_failed",
                    actor_user_id=removed_by_user_id,
                    target_type="project",
                    target_id=project_id,
                    metadata={"reason": "not_found", "detail": "User not in project", "user_id": str(user_id)},
                )
            )
        return False

    db.delete(user_project)
    db.commit()

    if removed_by_user_id:
        from app.events.project_events import UserRemovedFromProjectEvent

        event = UserRemovedFromProjectEvent(
            project_id=project_id,
            user_id=user_id,
            removed_by_user_id=removed_by_user_id,
            db=db,
            is_self_removal=is_self_removal,
        )
        EventManager.emit(event)

        # Emit domain event for audit
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="project.member_removed",
                actor_user_id=removed_by_user_id,
                target_type="project",
                target_id=project_id,
                metadata={"removed_user_id": str(user_id), "is_self_removal": is_self_removal},
            )
        )

    return True


def update_user_role_in_project(
    db: Session,
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    new_role: str,
    actor_user_id: uuid.UUID | None = None,
) -> Optional[UserProject]:
    """
    Update a user's role in a project
    """
    user_project = db.query(UserProject).filter(and_(UserProject.project_id == project_id, UserProject.user_id == user_id)).first()

    if not user_project:
        if actor_user_id:
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="project.member_role_update_failed",
                    actor_user_id=actor_user_id,
                    target_type="project",
                    target_id=project_id,
                    metadata={"reason": "not_found", "detail": "User not in project", "user_id": str(user_id)},
                )
            )
        return None

    user_project.role = new_role
    db.commit()
    db.refresh(user_project)

    # Emit domain event
    if actor_user_id:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="project.member_role_updated",
                actor_user_id=actor_user_id,
                target_type="project",
                target_id=project_id,
                metadata={"user_id": str(user_id), "new_role": new_role},
            )
        )

    return user_project


def get_project_members(db: Session, project_id: uuid.UUID) -> List[UserProject]:
    """
    Get all members of a project
    """
    return db.query(UserProject).options(joinedload(UserProject.user)).filter(UserProject.project_id == project_id).all()


def is_user_in_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """
    Check if a user is a member of a project
    """
    count = db.query(UserProject).filter(and_(UserProject.project_id == project_id, UserProject.user_id == user_id)).count()
    return count > 0


def get_user_role_in_project(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> Optional[str]:
    """
    Get a user's role in a project
    """
    user_project = db.query(UserProject).filter(and_(UserProject.project_id == project_id, UserProject.user_id == user_id)).first()
    return user_project.role if user_project else None


# Bulk operations
def bulk_add_users_to_project(db: Session, project_id: uuid.UUID, users_data: List[UserProjectCreate], added_by_user_id: uuid.UUID = None) -> List[Dict[str, Any]]:
    """
    Bulk add users to a project
    """
    # Validate that project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return [
            {
                "success": False,
                "user_id": str(user_data.user_id),
                "message": "Project not found",
            }
            for user_data in users_data
        ]

    results = []

    for user_data in users_data:
        try:
            user_project = add_user_to_project(db, project_id, user_data.user_id, user_data.role, added_by_user_id)
            if user_project:
                results.append(
                    {
                        "success": True,
                        "user_id": str(user_data.user_id),
                        "message": f"User {user_data.user_id} added to project",
                    }
                )
            else:
                results.append(
                    {
                        "success": False,
                        "user_id": str(user_data.user_id),
                        "message": "Failed to add user (user or project not found)",
                    }
                )
        except Exception as e:
            results.append(
                {
                    "success": False,
                    "user_id": str(user_data.user_id),
                    "message": f"Error: {str(e)}",
                }
            )

    return results


def bulk_remove_users_from_project(db: Session, project_id: uuid.UUID, user_ids: List[uuid.UUID]) -> List[Dict[str, Any]]:
    """
    Bulk remove users from a project
    """
    # Validate that project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return [
            {
                "success": False,
                "user_id": str(user_id),
                "message": "Project not found",
            }
            for user_id in user_ids
        ]

    results = []

    for user_id in user_ids:
        try:
            success = remove_user_from_project(db, project_id, user_id)
            if success:
                results.append(
                    {
                        "success": True,
                        "user_id": str(user_id),
                        "message": f"User {user_id} removed from project",
                    }
                )
            else:
                results.append(
                    {
                        "success": False,
                        "user_id": str(user_id),
                        "message": "User not found in project",
                    }
                )
        except Exception as e:
            results.append(
                {
                    "success": False,
                    "user_id": str(user_id),
                    "message": f"Error: {str(e)}",
                }
            )

    return results


# Helper functions for response formatting
def format_project_response(project: Project) -> ProjectResponse:
    """
    Format project data for API response
    """
    member_count = len(project.users) if hasattr(project, "users") else None

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        is_archived=project.is_archived,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        member_count=member_count,
    )


def format_project_with_members_response(project: Project) -> ProjectWithMembers:
    """
    Format project with members data for API response
    """
    base_response = format_project_response(project)

    members = []
    if hasattr(project, "users"):
        for user_project in project.users:
            members.append(
                UserProjectResponse(
                    user_id=user_project.user_id,
                    project_id=user_project.project_id,
                    role=user_project.role,
                    joined_at=user_project.joined_at,
                    user={
                        "id": user_project.user.id,
                        "email": user_project.user.email,
                        "name": user_project.user.name,
                        "avatar_url": user_project.user.avatar_url,
                        "position": user_project.user.position,
                    }
                    if user_project.user
                    else None,
                )
            )

    return ProjectWithMembers(
        **base_response.model_dump(),
        members=members,
    )


def format_user_project_response(user_project: UserProject) -> UserProjectResponse:
    """
    Format user-project relationship data for API response
    """
    return UserProjectResponse(
        user_id=user_project.user_id,
        project_id=user_project.project_id,
        role=user_project.role,
        joined_at=user_project.joined_at,
        user={
            "id": user_project.user.id,
            "email": user_project.user.email,
            "name": user_project.user.name,
            "avatar_url": user_project.user.avatar_url,
            "position": user_project.user.position,
        }
        if user_project.user
        else None,
    )
