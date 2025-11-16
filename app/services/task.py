import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.events.domain_events import BaseDomainEvent, build_diff
from app.models.meeting import Meeting, ProjectMeeting
from app.models.project import Project, UserProject
from app.models.task import Task, TaskProject
from app.models.user import User  # noqa: F401 (may be used in relationship loading hints)
from app.schemas.project import ProjectResponse
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.schemas.user import UserResponse
from app.services.event_manager import EventManager
from app.services.notification import create_notifications_bulk, send_fcm_notification


def check_task_access(db: Session, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return False

    # Direct access if user is creator or assignee
    if task.creator_id == user_id or task.assignee_id == user_id:
        return True

    # Check if user has access to any project linked to the task
    user_projects = db.query(Project.id).join(Project.users).filter(Project.users.any(user_id=user_id)).subquery()

    # Check if user has access to the meeting linked to the task
    if task.meeting_id:
        meeting_access = (
            db.query(ProjectMeeting)
            .join(Project, ProjectMeeting.project_id == Project.id)
            .join(Project.users)
            .filter(
                ProjectMeeting.meeting_id == task.meeting_id,
                Project.users.any(user_id=user_id),
            )
            .first()
            is not None
        )
        if meeting_access:
            return True

    # Check project access
    project_access = db.query(TaskProject).filter(TaskProject.task_id == task_id, TaskProject.project_id.in_(user_projects)).first() is not None

    return project_access


def create_task(db: Session, task_data: TaskCreate, creator_id: uuid.UUID) -> Task:
    if task_data.meeting_id:
        # Check if user has access to the meeting
        meeting_projects = db.query(ProjectMeeting.project_id).filter(ProjectMeeting.meeting_id == task_data.meeting_id).subquery()
        user_access = db.query(Project).join(Project.users).filter(Project.id.in_(meeting_projects), Project.users.any(user_id=creator_id)).first()
        if not user_access:
            # Audit failure (permission denied)
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="task.create_failed",
                    actor_user_id=creator_id,
                    target_type="task",
                    target_id=None,
                    metadata={"reason": "permission_denied", "detail": "No access to meeting", "meeting_id": str(task_data.meeting_id)},
                )
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to meeting")

    if task_data.project_ids:
        # Check if user has access to all specified projects
        for project_id in task_data.project_ids:
            user_project = db.query(Project).join(Project.users).filter(Project.id == project_id, Project.users.any(user_id=creator_id)).first()
            if not user_project:
                # Audit failure (permission denied)
                EventManager.emit_domain_event(
                    BaseDomainEvent(
                        event_name="task.create_failed",
                        actor_user_id=creator_id,
                        target_type="task",
                        target_id=None,
                        metadata={"reason": "permission_denied", "detail": f"No access to project {project_id}", "project_id": str(project_id)},
                    )
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"No access to project {project_id}",
                )

    task = Task(**task_data.model_dump(exclude={"project_ids"}), creator_id=creator_id)
    db.add(task)
    db.commit()
    db.refresh(task)

    # Emit domain event
    try:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="task.created",
                actor_user_id=creator_id,
                target_type="task",
                target_id=task.id,
                metadata={
                    "title": task.title,
                    "assignee_id": str(task.assignee_id) if task.assignee_id else None,
                    "project_ids": [str(pid) for pid in task_data.project_ids],
                    "meeting_id": str(task_data.meeting_id) if task_data.meeting_id else None,
                },
            )
        )
    except Exception:
        pass

    # Create project links
    for project_id in task_data.project_ids:
        task_project = TaskProject(task_id=task.id, project_id=project_id)
        db.add(task_project)
    db.commit()

    # Send notification to assignee if assigned
    if task_data.assignee_id:
        try:
            create_notifications_bulk(
                db,
                [task_data.assignee_id],
                type="task_assigned",
                payload={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "assigned_by": str(creator_id),
                },
            )
            send_fcm_notification(
                [task_data.assignee_id],
                "Task Assigned",
                f"You have been assigned to task: {task.title}",
                {"task_id": str(task.id), "type": "task_assigned"},
            )
        except Exception as e:
            print(f"Failed to send task assignment notification: {e}")

    return task


def get_tasks(
    db: Session,
    user_id: uuid.UUID,
    title: Optional[str] = None,
    status: Optional[str] = None,
    creator_id: Optional[uuid.UUID] = None,
    assignee_id: Optional[uuid.UUID] = None,
    due_date_gte: Optional[str] = None,
    due_date_lte: Optional[str] = None,
    created_at_gte: Optional[str] = None,
    created_at_lte: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> Tuple[List[Task], int]:
    query = db.query(Task).options(
        selectinload(Task.creator),
        selectinload(Task.assignee),
        selectinload(Task.projects).selectinload(TaskProject.project),
    )

    # Apply filters
    if title:
        query = query.filter(Task.title.ilike(f"%{title}%"))
    if status:
        query = query.filter(Task.status == status)
    if creator_id:
        query = query.filter(Task.creator_id == creator_id)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    if due_date_gte:
        from datetime import datetime

        query = query.filter(Task.due_date >= datetime.fromisoformat(due_date_gte))
    if due_date_lte:
        from datetime import datetime

        query = query.filter(Task.due_date <= datetime.fromisoformat(due_date_lte))
    if created_at_gte:
        from datetime import datetime

        query = query.filter(Task.created_at >= datetime.fromisoformat(created_at_gte))
    if created_at_lte:
        from datetime import datetime

        query = query.filter(Task.created_at <= datetime.fromisoformat(created_at_lte))

    # Filter by user access (projects/meetings user has access to)
    user_projects = db.query(Project.id).join(Project.users).filter(Project.users.any(user_id=user_id)).subquery()
    user_meetings = db.query(Meeting.id).join(ProjectMeeting, Meeting.id == ProjectMeeting.meeting_id).join(Project, ProjectMeeting.project_id == Project.id).join(Project.users).filter(Project.users.any(user_id=user_id)).subquery()

    task_projects_subquery = db.query(TaskProject.task_id).filter(TaskProject.project_id.in_(user_projects)).subquery()

    query = query.filter((Task.creator_id == user_id) | (Task.assignee_id == user_id) | (Task.id.in_(task_projects_subquery)) | (Task.meeting_id.in_(user_meetings)))

    total = query.count()
    offset = (page - 1) * limit
    tasks = query.offset(offset).limit(limit).all()

    return tasks, total


def get_task(db: Session, task_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Task]:
    if not check_task_access(db, task_id, user_id):
        return None

    return (
        db.query(Task)
        .options(
            selectinload(Task.creator),
            selectinload(Task.assignee),
            selectinload(Task.projects).selectinload(TaskProject.project),
        )
        .filter(Task.id == task_id)
        .first()
    )


def update_task(db: Session, task_id: uuid.UUID, task_data: TaskUpdate, user_id: uuid.UUID) -> Task:
    if not check_task_access(db, task_id, user_id):
        # Audit failure
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="task.update_failed",
                actor_user_id=user_id,
                target_type="task",
                target_id=task_id,
                metadata={"reason": "permission_denied", "detail": "No access to task"},
            )
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to task")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="task.update_failed",
                actor_user_id=user_id,
                target_type="task",
                target_id=task_id,
                metadata={"reason": "not_found", "detail": "Task not found"},
            )
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    old_assignee_id = task.assignee_id
    old_status = task.status

    updates = task_data.model_dump(exclude_unset=True)
    original = {k: getattr(task, k, None) for k in updates.keys()}
    for key, value in updates.items():
        if hasattr(task, key):
            setattr(task, key, value)

    db.commit()
    db.refresh(task)

    # Emit domain event with diff
    try:
        diff = build_diff(original, {k: getattr(task, k, None) for k in updates.keys()})
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="task.updated",
                actor_user_id=user_id,
                target_type="task",
                target_id=task.id,
                metadata={"diff": diff},
            )
        )
    except Exception:
        pass

    # Send notifications for changes
    try:
        # Notify assignee if newly assigned
        if "assignee_id" in updates and updates["assignee_id"] and updates["assignee_id"] != old_assignee_id:
            create_notifications_bulk(
                db,
                [updates["assignee_id"]],
                type="task_assigned",
                payload={
                    "task_id": str(task.id),
                    "task_title": task.title,
                    "assigned_by": str(user_id),
                },
            )
            send_fcm_notification(
                [updates["assignee_id"]],
                "Task Assigned",
                f"You have been assigned to task: {task.title}",
                {"task_id": str(task.id), "type": "task_assigned"},
            )

        # Notify when status changes
        if "status" in updates and updates["status"] != old_status:
            # Get all users with access to this task (creator, assignee, project/meeting users)
            notify_user_ids = set()

            # Add creator and assignee
            if task.creator_id:
                notify_user_ids.add(task.creator_id)
            if task.assignee_id:
                notify_user_ids.add(task.assignee_id)

            # Add project users (collect actual user UUIDs)
            task_projects = db.query(TaskProject.project_id).filter(TaskProject.task_id == task_id).subquery()
            project_user_ids = db.query(UserProject.user_id).filter(UserProject.project_id.in_(task_projects)).all()
            for (uid,) in project_user_ids:
                notify_user_ids.add(uid)

            # Add meeting users (collect actual user UUIDs)
            if task.meeting_id:
                meeting_projects = db.query(ProjectMeeting.project_id).filter(ProjectMeeting.meeting_id == task.meeting_id).subquery()
                meeting_user_ids = db.query(UserProject.user_id).filter(UserProject.project_id.in_(meeting_projects)).all()
                for (uid,) in meeting_user_ids:
                    notify_user_ids.add(uid)

            # Remove current user from notification list
            notify_user_ids.discard(user_id)

            if notify_user_ids:
                create_notifications_bulk(
                    db,
                    list(notify_user_ids),
                    type="task_updated",
                    payload={
                        "task_id": str(task.id),
                        "task_title": task.title,
                        "old_status": old_status,
                        "new_status": updates["status"],
                        "updated_by": str(user_id),
                    },
                )
                send_fcm_notification(
                    list(notify_user_ids),
                    "Task Updated",
                    f"Task '{task.title}' status changed to {updates['status']}",
                    {"task_id": str(task.id), "type": "task_updated"},
                )
    except Exception as e:
        print(f"Failed to send task update notification: {e}")

    return task


def delete_task(db: Session, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    if not check_task_access(db, task_id, user_id):
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="task.delete_failed",
                actor_user_id=user_id,
                target_type="task",
                target_id=task_id,
                metadata={"reason": "permission_denied", "detail": "No access to task"},
            )
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to task")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="task.delete_failed",
                actor_user_id=user_id,
                target_type="task",
                target_id=task_id,
                metadata={"reason": "not_found", "detail": "Task not found"},
            )
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Delete project links first
    db.query(TaskProject).filter(TaskProject.task_id == task_id).delete()

    # Delete task
    db.delete(task)
    db.commit()
    # Emit domain event success
    try:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="task.deleted",
                actor_user_id=user_id,
                target_type="task",
                target_id=task_id,
                metadata={},
            )
        )
    except Exception:
        pass
    return True


def bulk_create_tasks(db: Session, tasks_data: List[TaskCreate], creator_id: uuid.UUID) -> List[dict]:
    results = []
    for task_data in tasks_data:
        try:
            task = create_task(db, task_data, creator_id)
            results.append({"success": True, "id": task.id})
        except Exception as e:
            results.append({"success": False, "error": str(e)})
    return results


def bulk_update_tasks(db: Session, updates_data: List[dict], user_id: uuid.UUID) -> List[dict]:
    results = []
    for update_item in updates_data:
        try:
            task = update_task(db, update_item["id"], update_item["updates"], user_id)
            results.append({"success": True, "id": task.id})
        except Exception as e:
            results.append({"success": False, "id": update_item["id"], "error": str(e)})
    return results


def bulk_delete_tasks(db: Session, task_ids: List[uuid.UUID], user_id: uuid.UUID) -> List[dict]:
    results = []
    for task_id in task_ids:
        try:
            delete_task(db, task_id, user_id)
            results.append({"success": True, "id": task_id})
        except Exception as e:
            results.append({"success": False, "id": task_id, "error": str(e)})
    return results


def serialize_task(task: Task) -> TaskResponse:
    """Map a Task ORM object to TaskResponse with full ProjectResponse list.

    Ensures `projects` contains project objects (not TaskProject junctions)
    and expands `creator`/`assignee` to full UserResponse as requested.
    """
    projects: list[ProjectResponse] = []
    try:
        projects = [ProjectResponse.model_validate(tp.project, from_attributes=True) for tp in (task.projects or []) if getattr(tp, "project", None) is not None]
    except Exception:
        projects = []

    creator = UserResponse.model_validate(task.creator, from_attributes=True) if getattr(task, "creator", None) else None
    assignee = UserResponse.model_validate(task.assignee, from_attributes=True) if getattr(task, "assignee", None) else None

    return TaskResponse(
        id=task.id,
        title=task.title,
        description=task.description,
        status=task.status,
        creator_id=task.creator_id,
        assignee_id=task.assignee_id,
        meeting_id=task.meeting_id,
        due_date=task.due_date,
        reminder_at=task.reminder_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
        creator=creator,
        assignee=assignee,
        projects=projects,
    )
