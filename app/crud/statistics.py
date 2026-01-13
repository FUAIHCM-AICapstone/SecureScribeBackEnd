import logging
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, case, desc, func, or_
from sqlmodel import Session, select

from app.models.file import File
from app.models.meeting import AudioFile, Meeting, MeetingBot, MeetingStatus, Transcript
from app.models.project import Project, UserProject
from app.models.task import Task

logger = logging.getLogger(__name__)


def crud_get_task_aggregates(db: Session, scope_filter: Any) -> Tuple[int, int, int, int, int, int, int]:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = today_start + timedelta(days=7)

    agg_query = select(
        func.count(Task.id).label("total"),
        func.sum(case((Task.status == "todo", 1), else_=0)).label("todo"),
        func.sum(case((Task.status == "in_progress", 1), else_=0)).label("in_progress"),
        func.sum(case((Task.status == "done", 1), else_=0)).label("done"),
        func.sum(case((and_(Task.status != "done", Task.due_date < now, Task.due_date.isnot(None)), 1), else_=0)).label("overdue"),
        func.sum(case((and_(Task.due_date >= today_start, Task.due_date < today_start + timedelta(days=1)), 1), else_=0)).label("due_today"),
        func.sum(case((and_(Task.due_date >= today_start, Task.due_date < week_end), 1), else_=0)).label("due_this_week"),
    ).where(scope_filter)

    result = db.exec(agg_query).one()
    return (result.total or 0, result.todo or 0, result.in_progress or 0, result.done or 0, result.overdue or 0, result.due_today or 0, result.due_this_week or 0)


def crud_get_task_period_counts(db: Session, scope_filter: Any, start_date: datetime) -> Tuple[int, int]:
    period_query = select(
        func.count(Task.id).label("created"),
        func.sum(case((Task.status == "done", 1), else_=0)).label("completed"),
    ).where(scope_filter, Task.created_at >= start_date)
    result = db.exec(period_query).one()
    return (result.created or 0, result.completed or 0)


def crud_get_task_chart_data(db: Session, scope_filter: Any, start_date: Optional[datetime] = None) -> List[Tuple[Any, int, int]]:
    date_col = func.date_trunc("day", Task.created_at).label("day")
    chart_query = select(
        date_col,
        func.count(Task.id).label("count"),
        func.sum(case((Task.status == "done", 1), else_=0)).label("completed"),
    ).where(scope_filter)

    if start_date:
        chart_query = chart_query.where(Task.created_at >= start_date)

    chart_query = chart_query.group_by(date_col).order_by(date_col)
    return db.exec(chart_query).all()


def crud_get_meeting_ids_subquery(scope_filter: Any, start_date: Optional[datetime] = None):
    meeting_ids_subq = select(Meeting.id).where(scope_filter, Meeting.is_deleted == False)
    if start_date:
        meeting_ids_subq = meeting_ids_subq.where(Meeting.created_at >= start_date)
    return meeting_ids_subq.scalar_subquery()


def crud_get_meeting_count(db: Session, scope_filter: Any, start_date: Optional[datetime] = None) -> int:
    count_query = select(func.count(func.distinct(Meeting.id))).where(scope_filter, Meeting.is_deleted == False)
    if start_date:
        count_query = count_query.where(Meeting.created_at >= start_date)
    return db.exec(count_query).one() or 0


def crud_get_bot_usage_count(db: Session, meeting_ids_scalar) -> int:
    bot_statuses = ["joined", "recording", "complete", "ended"]
    bot_query = select(func.count(func.distinct(MeetingBot.meeting_id))).where(
        MeetingBot.meeting_id.in_(meeting_ids_scalar),
        MeetingBot.status.in_(bot_statuses),
    )
    return db.exec(bot_query).one() or 0


def crud_get_transcript_meeting_count(db: Session, meeting_ids_scalar) -> int:
    transcript_query = select(func.count(func.distinct(Transcript.meeting_id))).where(Transcript.meeting_id.in_(meeting_ids_scalar))
    return db.exec(transcript_query).one() or 0


def crud_get_upcoming_meetings_count(db: Session, scope_filter: Any) -> int:
    now = datetime.now(timezone.utc)
    upcoming_query = select(func.count(Meeting.id)).where(
        scope_filter,
        Meeting.is_deleted == False,
        Meeting.start_time > now,
        Meeting.status != MeetingStatus.cancelled,
    )
    return db.exec(upcoming_query).one() or 0


def crud_get_meeting_duration(db: Session, meeting_ids_scalar) -> int:
    duration_query = select(func.sum(AudioFile.duration_seconds)).where(
        AudioFile.meeting_id.in_(meeting_ids_scalar),
        AudioFile.is_deleted == False,
    )
    return db.exec(duration_query).one() or 0


def crud_get_meeting_chart_data(db: Session, scope_filter: Any, start_date: Optional[datetime] = None) -> List[Tuple[Any, int]]:
    date_col = func.date_trunc("day", Meeting.created_at).label("day")
    chart_query = select(
        date_col,
        func.count(func.distinct(Meeting.id)).label("count"),
    ).where(scope_filter, Meeting.is_deleted == False)

    if start_date:
        chart_query = chart_query.where(Meeting.created_at >= start_date)

    chart_query = chart_query.group_by(date_col).order_by(date_col)
    return db.exec(chart_query).all()


def crud_get_project_aggregates(db: Session, user_id: UUID) -> Tuple[int, int, int, int, int]:
    query = (
        select(
            func.count(Project.id).label("total"),
            func.sum(case((Project.is_archived == False, 1), else_=0)).label("active"),
            func.sum(case((Project.is_archived == True, 1), else_=0)).label("archived"),
            func.sum(case((UserProject.role.in_(["admin", "owner"]), 1), else_=0)).label("owned"),
            func.sum(case((UserProject.role == "member", 1), else_=0)).label("member"),
        )
        .select_from(Project)
        .join(UserProject)
        .where(UserProject.user_id == user_id)
    )

    result = db.exec(query).one()
    return (result.total or 0, result.active or 0, result.archived or 0, result.owned or 0, result.member or 0)


def crud_get_storage_aggregates(db: Session, user_id: UUID) -> Tuple[int, int]:
    query = select(
        func.count(File.id).label("count"),
        func.coalesce(func.sum(File.size_bytes), 0).label("size_bytes"),
    ).where(File.uploaded_by == user_id)
    result = db.exec(query).one()
    return (result.count or 0, result.size_bytes or 0)


def crud_get_file_type_breakdown(db: Session, user_id: UUID) -> dict:
    type_query = (
        select(
            File.mime_type,
            func.count(File.id).label("count"),
        )
        .where(
            File.uploaded_by == user_id,
            File.mime_type.isnot(None),
        )
        .group_by(File.mime_type)
        .order_by(desc(func.count(File.id)))
        .limit(10)
    )

    type_results = db.exec(type_query).all()
    return {mime: cnt for mime, cnt in type_results if mime}


def crud_get_meetings_by_time(db: Session, user_id: UUID, meeting_ids_in_projects, is_upcoming: bool = True, limit: int = 5) -> List[Meeting]:
    now = datetime.now(timezone.utc)
    query = select(Meeting).where(
        or_(Meeting.created_by == user_id, Meeting.id.in_(meeting_ids_in_projects)),
        Meeting.is_deleted == False,
    )
    if is_upcoming:
        query = query.where(Meeting.start_time > now, Meeting.status != MeetingStatus.cancelled).order_by(Meeting.start_time)
    else:
        query = query.where(Meeting.start_time < now).order_by(desc(Meeting.start_time))
    return db.exec(query.limit(limit)).all()


def crud_get_priority_tasks(db: Session, user_id: UUID) -> List[Task]:
    now = datetime.now(timezone.utc)
    tasks_query = (
        select(Task)
        .where(
            or_(Task.assignee_id == user_id, Task.creator_id == user_id),
            Task.status != "done",
        )
        .order_by(
            case((and_(Task.due_date < now, Task.due_date.isnot(None)), 0), else_=1),
            Task.due_date.asc().nulls_last(),
        )
        .limit(5)
    )
    return db.exec(tasks_query).all()


def crud_get_active_projects(db: Session, user_id: UUID, member_count_subq, task_count_subq, meeting_count_subq):
    projects_query = (
        select(
            Project,
            UserProject.role,
            UserProject.joined_at,
            func.coalesce(member_count_subq.c.member_count, 0).label("member_count"),
            func.coalesce(task_count_subq.c.task_count, 0).label("task_count"),
            func.coalesce(meeting_count_subq.c.meeting_count, 0).label("meeting_count"),
        )
        .join(UserProject)
        .outerjoin(member_count_subq, Project.id == member_count_subq.c.project_id)
        .outerjoin(task_count_subq, Project.id == task_count_subq.c.project_id)
        .outerjoin(meeting_count_subq, Project.id == meeting_count_subq.c.project_id)
        .where(
            UserProject.user_id == user_id,
            Project.is_archived == False,
        )
        .order_by(desc(UserProject.joined_at))
        .limit(5)
    )

    return db.exec(projects_query).all()


def crud_get_summary_task_counts(db: Session, scope_filter: Any) -> Tuple[int, int]:
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(hours=24)

    task_query = select(
        func.count(Task.id).label("total"),
        func.sum(
            case(
                (
                    and_(
                        Task.status != "done",
                        or_(
                            and_(Task.due_date < now, Task.due_date.isnot(None)),
                            and_(Task.due_date >= now, Task.due_date < tomorrow),
                        ),
                    ),
                    1,
                ),
                else_=0,
            )
        ).label("pending"),
    ).where(scope_filter)
    result = db.exec(task_query).one()
    return (result.total or 0, result.pending or 0)


def crud_get_summary_meeting_counts(db: Session, scope_filter: Any) -> Tuple[int, int]:
    now = datetime.now(timezone.utc)
    tomorrow = now + timedelta(hours=24)

    meeting_query = select(
        func.count(Meeting.id).label("total"),
        func.sum(case((and_(Meeting.start_time > now, Meeting.start_time < tomorrow), 1), else_=0)).label("upcoming_24h"),
    ).where(scope_filter, Meeting.is_deleted == False)
    result = db.exec(meeting_query).one()
    return (result.total or 0, result.upcoming_24h or 0)


def crud_get_summary_project_count(db: Session, user_id: UUID) -> int:
    project_query = (
        select(func.count(Project.id))
        .join(UserProject)
        .where(
            UserProject.user_id == user_id,
            Project.is_archived == False,
        )
    )
    return db.exec(project_query).one() or 0
