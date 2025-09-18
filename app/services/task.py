import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models.meeting import Meeting, ProjectMeeting
from app.models.project import Project
from app.models.task import Task, TaskProject
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.notification import create_notifications_bulk, send_fcm_notification


def check_task_access(db: Session, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return False

    # Check if user has access to any project linked to the task
    task_projects = db.query(TaskProject.project_id).filter(TaskProject.task_id == task_id).subquery()
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
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to meeting")

    if task_data.project_ids:
        # Check if user has access to all specified projects
        for project_id in task_data.project_ids:
            user_project = db.query(Project).join(Project.users).filter(Project.id == project_id, Project.users.any(user_id=creator_id)).first()
            if not user_project:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"No access to project {project_id}",
                )

    task = Task(**task_data.model_dump(exclude={"project_ids"}), creator_id=creator_id)
    db.add(task)
    db.commit()
    db.refresh(task)

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to task")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    old_assignee_id = task.assignee_id
    old_status = task.status

    updates = task_data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if hasattr(task, key):
            setattr(task, key, value)

    db.commit()
    db.refresh(task)

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

            # Add project users
            task_projects = db.query(TaskProject.project_id).filter(TaskProject.task_id == task_id).subquery()
            project_users = db.query(Project.users.any(user_id=user_id).label("user_id")).filter(Project.id.in_(task_projects)).all()
            for pu in project_users:
                notify_user_ids.add(pu.user_id)

            # Add meeting users
            if task.meeting_id:
                meeting_projects = db.query(ProjectMeeting.project_id).filter(ProjectMeeting.meeting_id == task.meeting_id).subquery()
                meeting_users = db.query(Project.users.any(user_id=user_id).label("user_id")).filter(Project.id.in_(meeting_projects)).all()
                for mu in meeting_users:
                    notify_user_ids.add(mu.user_id)

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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to task")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Delete project links first
    db.query(TaskProject).filter(TaskProject.task_id == task_id).delete()

    # Delete task
    db.delete(task)
    db.commit()
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
