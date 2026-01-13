import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session, selectinload

from app.models.meeting import Meeting, ProjectMeeting
from app.models.project import Project, UserProject
from app.models.task import Task, TaskProject


def crud_create_task(db: Session, **task_data) -> Task:
    task = Task(**task_data)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def crud_get_task(db: Session, task_id: uuid.UUID) -> Optional[Task]:
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


def crud_get_tasks(
    db: Session,
    user_id: uuid.UUID,
    title: Optional[str] = None,
    status: Optional[str] = None,
    creator_id: Optional[uuid.UUID] = None,
    assignee_id: Optional[uuid.UUID] = None,
    due_date_gte: Optional[str] = None,
    due_date_lte: Optional[str] = None,
    meeting_id: Optional[uuid.UUID] = None,
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

    if title:
        query = query.filter(Task.title.ilike(f"%{title}%"))
    if status:
        query = query.filter(Task.status == status)
    if creator_id:
        query = query.filter(Task.creator_id == creator_id)
    if assignee_id:
        query = query.filter(Task.assignee_id == assignee_id)
    if due_date_gte:
        query = query.filter(Task.due_date >= datetime.fromisoformat(due_date_gte))
    if due_date_lte:
        query = query.filter(Task.due_date <= datetime.fromisoformat(due_date_lte))
    if created_at_gte:
        query = query.filter(Task.created_at >= datetime.fromisoformat(created_at_gte))
    if created_at_lte:
        query = query.filter(Task.created_at <= datetime.fromisoformat(created_at_lte))

    user_projects = db.query(Project.id).join(Project.users).filter(Project.users.any(user_id=user_id)).subquery()
    user_meetings = db.query(Meeting.id).join(ProjectMeeting, Meeting.id == ProjectMeeting.meeting_id).join(Project, ProjectMeeting.project_id == Project.id).join(Project.users).filter(Project.users.any(user_id=user_id)).subquery()

    task_projects_subquery = db.query(TaskProject.task_id).filter(TaskProject.project_id.in_(user_projects)).subquery()

    query = query.filter((Task.creator_id == user_id) | (Task.assignee_id == user_id) | (Task.id.in_(task_projects_subquery)) | (Task.meeting_id.in_(user_meetings)))
    if meeting_id:
        query = query.filter(Task.meeting_id == meeting_id)
    total = query.count()
    query = query.order_by(Task.created_at.desc(), Task.updated_at.desc())
    offset = (page - 1) * limit
    tasks = query.offset(offset).limit(limit).all()

    return tasks, total


def crud_update_task(db: Session, task_id: uuid.UUID, **updates) -> Optional[Task]:
    task = crud_get_task(db, task_id)
    if not task:
        return None
    for key, value in updates.items():
        if hasattr(task, key):
            setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return task


def crud_delete_task(db: Session, task_id: uuid.UUID) -> bool:
    db.query(TaskProject).filter(TaskProject.task_id == task_id).delete()
    task = crud_get_task(db, task_id)
    if not task:
        return False
    db.delete(task)
    db.commit()
    return True


def crud_link_task_to_projects(db: Session, task_id: uuid.UUID, project_ids: List[uuid.UUID]) -> None:
    for project_id in project_ids:
        db.add(TaskProject(task_id=task_id, project_id=project_id))
    db.commit()


def crud_check_direct_access(task: Task, user_id: uuid.UUID) -> bool:
    return task.creator_id == user_id or task.assignee_id == user_id


def crud_check_project_access(db: Session, task_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    user_projects = db.query(Project.id).join(Project.users).filter(Project.users.any(user_id=user_id)).subquery()
    return db.query(TaskProject).filter(TaskProject.task_id == task_id, TaskProject.project_id.in_(user_projects)).first() is not None


def crud_check_meeting_access(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting and meeting.created_by == user_id:
        return True
    linked_projects = db.query(ProjectMeeting.project_id).filter(ProjectMeeting.meeting_id == meeting_id).subquery()
    return db.query(UserProject).filter(UserProject.user_id == user_id, UserProject.project_id.in_(linked_projects)).first() is not None


def crud_check_user_project_access(db: Session, project_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    return db.query(Project).join(Project.users).filter(Project.id == project_id, Project.users.any(user_id=user_id)).first() is not None


def crud_get_task_status_notifyees(db: Session, task_id: uuid.UUID, task: Task, user_id: uuid.UUID) -> set:
    notify_user_ids = set()
    if task.creator_id:
        notify_user_ids.add(task.creator_id)
    if task.assignee_id:
        notify_user_ids.add(task.assignee_id)

    task_projects = db.query(TaskProject.project_id).filter(TaskProject.task_id == task_id).subquery()
    project_user_ids = db.query(UserProject.user_id).filter(UserProject.project_id.in_(task_projects)).all()
    notify_user_ids.update(uid for (uid,) in project_user_ids)

    if task.meeting_id:
        meeting_projects = db.query(ProjectMeeting.project_id).filter(ProjectMeeting.meeting_id == task.meeting_id).subquery()
        meeting_user_ids = db.query(UserProject.user_id).filter(UserProject.project_id.in_(meeting_projects)).all()
        notify_user_ids.update(uid for (uid,) in meeting_user_ids)

    notify_user_ids.discard(user_id)
    return notify_user_ids
