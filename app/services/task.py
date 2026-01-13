import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.task import (
    crud_check_direct_access,
    crud_check_meeting_access,
    crud_check_project_access,
    crud_check_user_project_access,
    crud_create_task,
    crud_delete_task,
    crud_get_task,
    crud_get_task_status_notifyees,
    crud_get_tasks,
    crud_link_task_to_projects,
    crud_update_task,
)
from app.events.domain_events import BaseDomainEvent, build_diff
from app.models.task import Task
from app.models.user import User  # noqa: F401
from app.schemas.project import ProjectResponse
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.schemas.user import UserResponse
from app.services.event_manager import EventManager
from app.services.notification import create_notifications_bulk, send_fcm_notification

ERROR_NO_TASK_ACCESS = "No access to task"
ERROR_TASK_NOT_FOUND = "Task not found"


def check_task_access(db: Session, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    task = crud_get_task(db, task_id)
    if not task:
        return False
    if crud_check_direct_access(task, user_id):
        return True
    if task.meeting_id and crud_check_meeting_access(db, task.meeting_id, user_id):
        return True
    return crud_check_project_access(db, task_id, user_id)


def _validate_meeting_and_projects(db: Session, task_data: TaskCreate, creator_id: uuid.UUID) -> None:
    if task_data.meeting_id and not crud_check_meeting_access(db, task_data.meeting_id, creator_id):
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
    for project_id in task_data.project_ids:
        if not crud_check_user_project_access(db, project_id, creator_id):
            EventManager.emit_domain_event(
                BaseDomainEvent(
                    event_name="task.create_failed",
                    actor_user_id=creator_id,
                    target_type="task",
                    target_id=None,
                    metadata={"reason": "permission_denied", "detail": f"No access to project {project_id}", "project_id": str(project_id)},
                )
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"No access to project {project_id}")


def _emit_task_created_event(creator_id: uuid.UUID, task: Task, task_data: TaskCreate) -> None:
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
                    "meeting_id": (str(task_data.meeting_id) if task_data.meeting_id else None),
                },
            )
        )
    except Exception:
        pass


def _notify_assignee(db: Session, task: Task, creator_id: uuid.UUID) -> None:
    if not task.assignee_id:
        return
    try:
        creator = db.query(User).filter(User.id == creator_id).first()
        create_notifications_bulk(
            db,
            [task.assignee_id],
            type="task_assigned",
            payload={"task_id": str(task.id), "task_title": task.title, "assigned_by": str(creator.name)},
        )
        send_fcm_notification(
            [task.assignee_id],
            "Task Assigned",
            f"You have been assigned to task: {task.title}",
            {"task_id": str(task.id), "type": "task_assigned"},
        )
    except Exception as e:
        print(f"Failed to send task assignment notification: {e}")


def _notify_assignee_updated(db: Session, task: Task, assignee_id: uuid.UUID, user_id: uuid.UUID) -> None:
    try:
        create_notifications_bulk(
            db,
            [assignee_id],
            type="task_assigned",
            payload={"task_id": str(task.id), "task_title": task.title, "assigned_by": str(user_id)},
        )
        send_fcm_notification(
            [assignee_id],
            "Task Assigned",
            f"You have been assigned to task: {task.title}",
            {"task_id": str(task.id), "type": "task_assigned"},
        )
    except Exception as e:
        print(f"Failed to send assignment notification: {e}")


def _emit_update_event_and_notifications(
    db: Session,
    task: Task,
    original: dict,
    updates: dict,
    old_assignee_id: uuid.UUID,
    old_status: str,
    user_id: uuid.UUID,
) -> None:
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

    try:
        if "assignee_id" in updates and updates["assignee_id"] and updates["assignee_id"] != old_assignee_id:
            _notify_assignee_updated(db, task, updates["assignee_id"], user_id)
        if "status" in updates and updates["status"] != old_status:
            notify_user_ids = crud_get_task_status_notifyees(db, task.id, task, user_id)
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


def update_task(db: Session, task_id: uuid.UUID, task_data: TaskUpdate, user_id: uuid.UUID) -> Task:
    if not check_task_access(db, task_id, user_id):
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="task.update_failed",
                actor_user_id=user_id,
                target_type="task",
                target_id=task_id,
                metadata={"reason": "permission_denied", "detail": ERROR_NO_TASK_ACCESS},
            )
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_NO_TASK_ACCESS)
    task = crud_get_task(db, task_id)
    if not task:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="task.update_failed",
                actor_user_id=user_id,
                target_type="task",
                target_id=task_id,
                metadata={"reason": "not_found", "detail": ERROR_TASK_NOT_FOUND},
            )
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_TASK_NOT_FOUND)
    old_assignee_id = task.assignee_id
    old_status = task.status
    updates = task_data.model_dump(exclude_unset=True)
    original = {k: getattr(task, k, None) for k in updates.keys()}
    task = crud_update_task(db, task_id, **updates)
    _emit_update_event_and_notifications(db, task, original, updates, old_assignee_id, old_status, user_id)
    return task


def delete_task(db: Session, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    if not check_task_access(db, task_id, user_id):
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="task.delete_failed",
                actor_user_id=user_id,
                target_type="task",
                target_id=task_id,
                metadata={"reason": "permission_denied", "detail": ERROR_NO_TASK_ACCESS},
            )
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_NO_TASK_ACCESS)
    if not crud_get_task(db, task_id):
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="task.delete_failed",
                actor_user_id=user_id,
                target_type="task",
                target_id=task_id,
                metadata={"reason": "not_found", "detail": ERROR_TASK_NOT_FOUND},
            )
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_TASK_NOT_FOUND)
    crud_delete_task(db, task_id)
    try:
        EventManager.emit_domain_event(BaseDomainEvent(event_name="task.deleted", actor_user_id=user_id, target_type="task", target_id=task_id, metadata={}))
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
