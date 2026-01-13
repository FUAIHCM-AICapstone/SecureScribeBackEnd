import logging
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select

from app.crud.statistics import (
    crud_get_active_projects,
    crud_get_bot_usage_count,
    crud_get_file_type_breakdown,
    crud_get_meeting_chart_data,
    crud_get_meeting_count,
    crud_get_meeting_duration,
    crud_get_meeting_ids_subquery,
    crud_get_meetings_by_time,
    crud_get_priority_tasks,
    crud_get_project_aggregates,
    crud_get_storage_aggregates,
    crud_get_summary_meeting_counts,
    crud_get_summary_project_count,
    crud_get_summary_task_counts,
    crud_get_task_aggregates,
    crud_get_task_chart_data,
    crud_get_task_period_counts,
    crud_get_transcript_meeting_count,
    crud_get_upcoming_meetings_count,
)
from app.models.meeting import Meeting, ProjectMeeting
from app.models.project import UserProject
from app.models.task import Task, TaskProject
from app.schemas.statistics import (
    ChartDataPoint,
    DashboardPeriod,
    DashboardResponse,
    DashboardScope,
    MeetingStats,
    ProjectStats,
    QuickAccessData,
    QuickAccessMeeting,
    QuickAccessProject,
    QuickAccessTask,
    StorageStats,
    SummaryStats,
    TaskStats,
    TaskStatusBreakdown,
)

logger = logging.getLogger(__name__)


def get_date_range(period: DashboardPeriod) -> Optional[datetime]:
    now = datetime.now(timezone.utc)
    if period == DashboardPeriod.SEVEN_DAYS:
        return now - timedelta(days=7)
    elif period == DashboardPeriod.THIRTY_DAYS:
        return now - timedelta(days=30)
    elif period == DashboardPeriod.NINETY_DAYS:
        return now - timedelta(days=90)
    return None


def _fill_chart_data(data: List[Any], start_date: Optional[datetime]) -> List[ChartDataPoint]:
    if not start_date:
        return [ChartDataPoint(date=d.date() if hasattr(d, "date") else d, count=c, value=v) for d, c, v in data]

    data_map = {(d.date() if hasattr(d, "date") else d): (c, v) for d, c, v in data}
    result = []
    current_date = start_date.date() if hasattr(start_date, "date") else start_date
    end_date = datetime.now(timezone.utc).date()

    while current_date <= end_date:
        if current_date in data_map:
            count, value = data_map[current_date]
            result.append(ChartDataPoint(date=current_date, count=count, value=value))
        else:
            result.append(ChartDataPoint(date=current_date, count=0, value=0))
        current_date += timedelta(days=1)

    return result


def _build_task_scope_filter(user_id: UUID, scope: DashboardScope):
    if scope == DashboardScope.PROJECT:
        user_project_ids = select(UserProject.project_id).where(UserProject.user_id == user_id).scalar_subquery()
        task_ids_in_projects = select(TaskProject.task_id).where(TaskProject.project_id.in_(user_project_ids)).scalar_subquery()
        return Task.id.in_(task_ids_in_projects)
    else:
        from sqlalchemy import or_

        return or_(Task.assignee_id == user_id, Task.creator_id == user_id)


def _build_meeting_scope_filter(user_id: UUID, scope: DashboardScope):
    if scope == DashboardScope.PERSONAL:
        return Meeting.created_by == user_id
    elif scope == DashboardScope.PROJECT:
        user_project_ids = select(UserProject.project_id).where(UserProject.user_id == user_id).scalar_subquery()
        meeting_ids_in_projects = select(ProjectMeeting.meeting_id).where(ProjectMeeting.project_id.in_(user_project_ids)).scalar_subquery()
        return Meeting.id.in_(meeting_ids_in_projects)
    else:
        from sqlalchemy import or_

        user_project_ids = select(UserProject.project_id).where(UserProject.user_id == user_id).scalar_subquery()
        meeting_ids_in_projects = select(ProjectMeeting.meeting_id).where(ProjectMeeting.project_id.in_(user_project_ids)).scalar_subquery()
        return or_(Meeting.created_by == user_id, Meeting.id.in_(meeting_ids_in_projects))


def get_task_stats(db: Session, user_id: UUID, start_date: Optional[datetime], scope: DashboardScope) -> TaskStats:
    scope_filter = _build_task_scope_filter(user_id, scope)
    total, todo, in_progress, done, overdue, due_today, due_this_week = crud_get_task_aggregates(db, scope_filter)

    created_in_period, completed_in_period = 0, 0
    if start_date:
        created_in_period, completed_in_period = crud_get_task_period_counts(db, scope_filter, start_date)

    rate = (done / total * 100) if total > 0 else 0.0
    chart_results = crud_get_task_chart_data(db, scope_filter, start_date)
    formatted_chart_data = [(day, count, completed or 0) for day, count, completed in chart_results]
    chart_data = _fill_chart_data(formatted_chart_data, start_date)

    return TaskStats(
        total=total,
        status_breakdown=TaskStatusBreakdown(todo=todo, in_progress=in_progress, done=done),
        overdue_count=overdue,
        completion_rate=round(rate, 1),
        due_today=due_today,
        due_this_week=due_this_week,
        created_this_period=created_in_period,
        completed_this_period=completed_in_period,
        chart_data=chart_data,
    )


def get_meeting_stats(db: Session, user_id: UUID, start_date: Optional[datetime], scope: DashboardScope) -> MeetingStats:
    scope_filter = _build_meeting_scope_filter(user_id, scope)
    meeting_ids_scalar = crud_get_meeting_ids_subquery(scope_filter, start_date)

    total_count = crud_get_meeting_count(db, scope_filter, start_date)
    bot_usage = crud_get_bot_usage_count(db, meeting_ids_scalar)
    meetings_with_transcript = crud_get_transcript_meeting_count(db, meeting_ids_scalar)
    upcoming_count = crud_get_upcoming_meetings_count(db, scope_filter)
    total_seconds = crud_get_meeting_duration(db, meeting_ids_scalar)

    total_minutes = int(total_seconds / 60)
    avg_minutes = round(total_minutes / total_count, 1) if total_count > 0 else 0.0
    bot_usage_rate = round((bot_usage / total_count) * 100, 1) if total_count > 0 else 0.0

    chart_results = crud_get_meeting_chart_data(db, scope_filter, start_date)
    formatted_chart_data = [(d, c, 0) for d, c in chart_results]
    chart_data = _fill_chart_data(formatted_chart_data, start_date)

    return MeetingStats(
        total_count=total_count,
        total_duration_minutes=total_minutes,
        average_duration_minutes=avg_minutes,
        bot_usage_count=bot_usage,
        bot_usage_rate=bot_usage_rate,
        meetings_with_transcript=meetings_with_transcript,
        upcoming_count=upcoming_count,
        chart_data=chart_data,
    )


def get_project_stats(db: Session, user_id: UUID) -> ProjectStats:
    total, active, archived, owned, member = crud_get_project_aggregates(db, user_id)
    return ProjectStats(
        total_count=total,
        active_count=active,
        archived_count=archived,
        owned_count=owned,
        member_count=member,
    )


def get_storage_stats(db: Session, user_id: UUID) -> StorageStats:
    count, size_bytes = crud_get_storage_aggregates(db, user_id)
    size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes else 0.0
    files_by_type = crud_get_file_type_breakdown(db, user_id)

    return StorageStats(
        total_files=count,
        total_size_bytes=size_bytes,
        total_size_mb=size_mb,
        files_by_type=files_by_type,
    )


def get_quick_access(db: Session, user_id: UUID) -> QuickAccessData:
    user_project_ids = select(UserProject.project_id).where(UserProject.user_id == user_id).scalar_subquery()
    meeting_ids_in_projects = select(ProjectMeeting.meeting_id).where(ProjectMeeting.project_id.in_(user_project_ids)).scalar_subquery()

    upcoming_meetings = crud_get_meetings_by_time(db, user_id, meeting_ids_in_projects, is_upcoming=True)
    recent_meetings = crud_get_meetings_by_time(db, user_id, meeting_ids_in_projects, is_upcoming=False)

    def format_meetings(meetings: List[Meeting]) -> List[QuickAccessMeeting]:
        result = []
        for m in meetings:
            project_names = [pm.project.name for pm in m.projects if pm.project] if m.projects else []
            has_recording = bool(m.bot and m.bot.status in ["complete", "ended", "recording"])
            result.append(
                QuickAccessMeeting(
                    id=m.id,
                    title=m.title,
                    start_time=m.start_time,
                    url=m.url,
                    project_names=project_names,
                    status=m.status,
                    has_transcript=bool(m.transcript),
                    has_recording=has_recording,
                )
            )
        return result

    priority_tasks = crud_get_priority_tasks(db, user_id)
    formatted_tasks = []
    now = datetime.now(timezone.utc)
    for t in priority_tasks:
        project_names = [tp.project.name for tp in t.projects if tp.project] if t.projects else []
        is_overdue = bool(t.due_date and t.due_date < now and t.status != "done")
        formatted_tasks.append(
            QuickAccessTask(
                id=t.id,
                title=t.title,
                due_date=t.due_date,
                priority=t.priority or "medium",
                status=t.status,
                project_names=project_names,
                is_overdue=is_overdue,
            )
        )

    member_count_subq = (
        select(
            UserProject.project_id,
            func.count(UserProject.user_id).label("member_count"),
        )
        .group_by(UserProject.project_id)
        .subquery()
    )

    task_count_subq = (
        select(
            TaskProject.project_id,
            func.count(TaskProject.task_id).label("task_count"),
        )
        .join(Task)
        .where(Task.status != "done")
        .group_by(TaskProject.project_id)
        .subquery()
    )

    meeting_count_subq = (
        select(
            ProjectMeeting.project_id,
            func.count(ProjectMeeting.meeting_id).label("meeting_count"),
        )
        .group_by(ProjectMeeting.project_id)
        .subquery()
    )

    projects_results = crud_get_active_projects(db, user_id, member_count_subq, task_count_subq, meeting_count_subq)
    formatted_projects = []
    for p, role, joined_at, member_count, task_count, meeting_count in projects_results:
        formatted_projects.append(
            QuickAccessProject(
                id=p.id,
                name=p.name,
                description=p.description,
                role=role,
                member_count=member_count,
                task_count=task_count,
                meeting_count=meeting_count,
                joined_at=joined_at,
            )
        )

    return QuickAccessData(
        upcoming_meetings=format_meetings(upcoming_meetings),
        recent_meetings=format_meetings(recent_meetings),
        priority_tasks=formatted_tasks,
        active_projects=formatted_projects,
    )


def get_summary_stats(db: Session, user_id: UUID, scope: DashboardScope) -> SummaryStats:
    task_scope_filter = _build_task_scope_filter(user_id, scope)
    task_total, task_pending = crud_get_summary_task_counts(db, task_scope_filter)

    meeting_scope_filter = _build_meeting_scope_filter(user_id, scope)
    meeting_total, upcoming_24h = crud_get_summary_meeting_counts(db, meeting_scope_filter)

    project_count = crud_get_summary_project_count(db, user_id)

    return SummaryStats(
        total_tasks=task_total,
        total_meetings=meeting_total,
        total_projects=project_count,
        pending_tasks=task_pending,
        upcoming_meetings_24h=upcoming_24h,
    )


def get_dashboard_stats(db: Session, user_id: UUID, period: DashboardPeriod, scope: DashboardScope) -> DashboardResponse:
    start_date = get_date_range(period)
    summary = get_summary_stats(db, user_id, scope)
    tasks = get_task_stats(db, user_id, start_date, scope)
    meetings = get_meeting_stats(db, user_id, start_date, scope)
    projects = get_project_stats(db, user_id)
    storage = get_storage_stats(db, user_id)
    quick_access = get_quick_access(db, user_id)

    return DashboardResponse(
        period=period,
        scope=scope,
        summary=summary,
        tasks=tasks,
        meetings=meetings,
        projects=projects,
        storage=storage,
        quick_access=quick_access,
    )
