import logging
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import and_, case, desc, func, or_
from sqlmodel import Session, select

from app.models.file import File
from app.models.meeting import AudioFile, Meeting, MeetingBot, MeetingStatus, ProjectMeeting, Transcript
from app.models.project import Project, UserProject
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


class StatisticsService:
    def __init__(self, db: Session, user_id: UUID):
        self.db = db
        self.user_id = user_id

    def get_date_range(self, period: DashboardPeriod) -> Optional[datetime]:
        now = datetime.now(timezone.utc)
        if period == DashboardPeriod.SEVEN_DAYS:
            return now - timedelta(days=7)
        elif period == DashboardPeriod.THIRTY_DAYS:
            return now - timedelta(days=30)
        elif period == DashboardPeriod.NINETY_DAYS:
            return now - timedelta(days=90)
        return None

    def _fill_chart_data(self, data: List[Any], start_date: Optional[datetime], period: DashboardPeriod) -> List[ChartDataPoint]:
        """Fill missing dates with zero values for charts"""
        if not start_date:
            # If 'all' time, just return what we have, or maybe limit to last 30 days for chart readability?
            # For 'all', let's just return the data we found sorted.
            return [ChartDataPoint(date=d.date() if hasattr(d, "date") else d, count=c, value=v) for d, c, v in data]

        # Create a map of existing data - convert datetime to date for keys
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

    def _build_task_scope_filter(self, scope: DashboardScope):
        """Build base filter conditions for task queries based on scope"""
        if scope == DashboardScope.PROJECT:
            # Tasks in user's projects
            user_project_ids = select(UserProject.project_id).where(UserProject.user_id == self.user_id).scalar_subquery()
            task_ids_in_projects = select(TaskProject.task_id).where(TaskProject.project_id.in_(user_project_ids)).scalar_subquery()
            return Task.id.in_(task_ids_in_projects)
        else:
            # Personal or Hybrid: tasks assigned to or created by user
            return or_(Task.assignee_id == self.user_id, Task.creator_id == self.user_id)

    def get_task_stats(self, start_date: Optional[datetime], scope: DashboardScope) -> TaskStats:
        """Get task statistics with optimized single-pass aggregation query"""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = today_start + timedelta(days=7)

        scope_filter = self._build_task_scope_filter(scope)

        # Single aggregation query for all counts
        agg_query = select(
            func.count(Task.id).label("total"),
            func.sum(case((Task.status == "todo", 1), else_=0)).label("todo"),
            func.sum(case((Task.status == "in_progress", 1), else_=0)).label("in_progress"),
            func.sum(case((Task.status == "done", 1), else_=0)).label("done"),
            func.sum(case((and_(Task.status != "done", Task.due_date < now, Task.due_date.isnot(None)), 1), else_=0)).label("overdue"),
            func.sum(case((and_(Task.due_date >= today_start, Task.due_date < today_start + timedelta(days=1)), 1), else_=0)).label("due_today"),
            func.sum(case((and_(Task.due_date >= today_start, Task.due_date < week_end), 1), else_=0)).label("due_this_week"),
        ).where(scope_filter)

        result = self.db.exec(agg_query).one()
        total = result.total or 0
        todo = result.todo or 0
        in_progress = result.in_progress or 0
        done = result.done or 0
        overdue = result.overdue or 0
        due_today = result.due_today or 0
        due_this_week = result.due_this_week or 0

        # Period-specific counts
        created_in_period = 0
        completed_in_period = 0
        if start_date:
            period_query = select(
                func.count(Task.id).label("created"),
                func.sum(case((Task.status == "done", 1), else_=0)).label("completed"),
            ).where(scope_filter, Task.created_at >= start_date)
            period_result = self.db.exec(period_query).one()
            created_in_period = period_result.created or 0
            completed_in_period = period_result.completed or 0

        # Completion rate
        rate = (done / total * 100) if total > 0 else 0.0

        # Chart data: Tasks created per day with completed count as value
        date_col = func.date_trunc("day", Task.created_at).label("day")
        chart_query = select(
            date_col,
            func.count(Task.id).label("count"),
            func.sum(case((Task.status == "done", 1), else_=0)).label("completed"),
        ).where(scope_filter)

        if start_date:
            chart_query = chart_query.where(Task.created_at >= start_date)

        chart_query = chart_query.group_by(date_col).order_by(date_col)
        chart_results = self.db.exec(chart_query).all()

        formatted_chart_data = [(day, count, completed or 0) for day, count, completed in chart_results]
        chart_data = self._fill_chart_data(formatted_chart_data, start_date, DashboardPeriod.ALL_TIME if not start_date else DashboardPeriod.SEVEN_DAYS)

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

    def _build_meeting_scope_filter(self, scope: DashboardScope):
        """Build base filter for meeting queries based on scope"""
        if scope == DashboardScope.PERSONAL:
            return Meeting.created_by == self.user_id
        else:
            # Hybrid or Project: meetings in user's projects
            user_project_ids = select(UserProject.project_id).where(UserProject.user_id == self.user_id).scalar_subquery()
            meeting_ids_in_projects = select(ProjectMeeting.meeting_id).where(ProjectMeeting.project_id.in_(user_project_ids)).scalar_subquery()
            return Meeting.id.in_(meeting_ids_in_projects)

    def get_meeting_stats(self, start_date: Optional[datetime], scope: DashboardScope) -> MeetingStats:
        """Get meeting statistics with optimized queries"""
        now = datetime.now(timezone.utc)
        scope_filter = self._build_meeting_scope_filter(scope)

        # Build meeting IDs subquery for reuse
        meeting_ids_subq = select(Meeting.id).where(scope_filter, Meeting.is_deleted == False)
        if start_date:
            meeting_ids_subq = meeting_ids_subq.where(Meeting.created_at >= start_date)
        meeting_ids_scalar = meeting_ids_subq.scalar_subquery()

        # Single aggregation query for meeting counts
        count_query = select(
            func.count(func.distinct(Meeting.id)).label("total"),
        ).where(scope_filter, Meeting.is_deleted == False)
        if start_date:
            count_query = count_query.where(Meeting.created_at >= start_date)
        total_count = self.db.exec(count_query).one() or 0

        # Bot usage count - meetings with successful bot sessions
        bot_statuses = ["joined", "recording", "complete", "ended"]
        bot_query = select(func.count(func.distinct(MeetingBot.meeting_id))).where(
            MeetingBot.meeting_id.in_(meeting_ids_scalar),
            MeetingBot.status.in_(bot_statuses),
        )
        bot_usage = self.db.exec(bot_query).one() or 0

        # Meetings with transcripts
        transcript_query = select(func.count(func.distinct(Transcript.meeting_id))).where(
            Transcript.meeting_id.in_(meeting_ids_scalar)
        )
        meetings_with_transcript = self.db.exec(transcript_query).one() or 0

        # Upcoming meetings count
        upcoming_query = select(func.count(Meeting.id)).where(
            scope_filter,
            Meeting.is_deleted == False,
            Meeting.start_time > now,
            Meeting.status != MeetingStatus.cancelled,
        )
        upcoming_count = self.db.exec(upcoming_query).one() or 0

        # Duration from AudioFiles
        duration_query = select(func.sum(AudioFile.duration_seconds)).where(
            AudioFile.meeting_id.in_(meeting_ids_scalar),
            AudioFile.is_deleted == False,
        )
        total_seconds = self.db.exec(duration_query).one() or 0
        total_minutes = int(total_seconds / 60)
        avg_minutes = round(total_minutes / total_count, 1) if total_count > 0 else 0.0
        bot_usage_rate = round((bot_usage / total_count) * 100, 1) if total_count > 0 else 0.0

        # Chart data: Meetings per day
        date_col = func.date_trunc("day", Meeting.created_at).label("day")
        chart_query = select(
            date_col,
            func.count(func.distinct(Meeting.id)).label("count"),
        ).where(scope_filter, Meeting.is_deleted == False)

        if start_date:
            chart_query = chart_query.where(Meeting.created_at >= start_date)

        chart_query = chart_query.group_by(date_col).order_by(date_col)
        chart_results = self.db.exec(chart_query).all()

        formatted_chart_data = [(d, c, 0) for d, c in chart_results]
        chart_data = self._fill_chart_data(formatted_chart_data, start_date, DashboardPeriod.ALL_TIME)

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

    def get_project_stats(self) -> ProjectStats:
        """Get project statistics with single aggregation query"""
        query = select(
            func.count(Project.id).label("total"),
            func.sum(case((Project.is_archived == False, 1), else_=0)).label("active"),
            func.sum(case((Project.is_archived == True, 1), else_=0)).label("archived"),
            func.sum(case((UserProject.role.in_(["admin", "owner"]), 1), else_=0)).label("owned"),
            func.sum(case((UserProject.role == "member", 1), else_=0)).label("member"),
        ).select_from(Project).join(UserProject).where(UserProject.user_id == self.user_id)

        result = self.db.exec(query).one()

        return ProjectStats(
            total_count=result.total or 0,
            active_count=result.active or 0,
            archived_count=result.archived or 0,
            owned_count=result.owned or 0,
            member_count=result.member or 0,
        )

    def get_storage_stats(self) -> StorageStats:
        """Get storage statistics with file type breakdown"""
        # Main aggregation
        query = select(
            func.count(File.id).label("count"),
            func.coalesce(func.sum(File.size_bytes), 0).label("size_bytes"),
        ).where(File.uploaded_by == self.user_id)
        result = self.db.exec(query).one()

        count = result.count or 0
        size_bytes = result.size_bytes or 0
        size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes else 0.0

        # File type breakdown (top MIME types)
        type_query = select(
            File.mime_type,
            func.count(File.id).label("count"),
        ).where(
            File.uploaded_by == self.user_id,
            File.mime_type.isnot(None),
        ).group_by(File.mime_type).order_by(desc(func.count(File.id))).limit(10)

        type_results = self.db.exec(type_query).all()
        files_by_type = {mime: cnt for mime, cnt in type_results if mime}

        return StorageStats(
            total_files=count,
            total_size_bytes=size_bytes,
            total_size_mb=size_mb,
            files_by_type=files_by_type,
        )

    def get_quick_access(self) -> QuickAccessData:
        """Get quick access data with optimized queries"""
        now = datetime.now(timezone.utc)

        # Get user's project IDs once
        user_project_ids = select(UserProject.project_id).where(UserProject.user_id == self.user_id).scalar_subquery()
        meeting_ids_in_projects = select(ProjectMeeting.meeting_id).where(ProjectMeeting.project_id.in_(user_project_ids)).scalar_subquery()

        # 1. Upcoming Meetings (Next 5)
        upcoming_query = select(Meeting).where(
            Meeting.id.in_(meeting_ids_in_projects),
            Meeting.start_time > now,
            Meeting.status != MeetingStatus.cancelled,
            Meeting.is_deleted == False,
        ).order_by(Meeting.start_time).limit(5)
        upcoming_meetings = self.db.exec(upcoming_query).all()

        # 2. Recent Meetings (Last 5)
        recent_query = select(Meeting).where(
            Meeting.id.in_(meeting_ids_in_projects),
            Meeting.start_time < now,
            Meeting.is_deleted == False,
        ).order_by(desc(Meeting.start_time)).limit(5)
        recent_meetings = self.db.exec(recent_query).all()

        def format_meetings(meetings: List[Meeting]) -> List[QuickAccessMeeting]:
            result = []
            for m in meetings:
                project_names = [pm.project.name for pm in m.projects if pm.project] if m.projects else []
                has_recording = bool(m.bot and m.bot.status in ["complete", "ended", "recording"])
                result.append(QuickAccessMeeting(
                    id=m.id,
                    title=m.title,
                    start_time=m.start_time,
                    url=m.url,
                    project_names=project_names,
                    status=m.status,
                    has_transcript=bool(m.transcript),
                    has_recording=has_recording,
                ))
            return result

        # 3. Priority Tasks (Overdue first, then by due date)
        tasks_query = select(Task).where(
            or_(Task.assignee_id == self.user_id, Task.creator_id == self.user_id),
            Task.status != "done",
        ).order_by(
            # Overdue tasks first
            case((and_(Task.due_date < now, Task.due_date.isnot(None)), 0), else_=1),
            Task.due_date.asc().nulls_last(),
        ).limit(5)
        tasks = self.db.exec(tasks_query).all()

        formatted_tasks = []
        for t in tasks:
            project_names = [tp.project.name for tp in t.projects if tp.project] if t.projects else []
            is_overdue = bool(t.due_date and t.due_date < now and t.status != "done")
            formatted_tasks.append(QuickAccessTask(
                id=t.id,
                title=t.title,
                due_date=t.due_date,
                priority=t.priority or "medium",
                status=t.status,
                project_names=project_names,
                is_overdue=is_overdue,
            ))

        # 4. Active Projects with counts (using subqueries for efficiency)
        # Get member counts per project
        member_count_subq = select(
            UserProject.project_id,
            func.count(UserProject.user_id).label("member_count"),
        ).group_by(UserProject.project_id).subquery()

        # Get task counts per project
        task_count_subq = select(
            TaskProject.project_id,
            func.count(TaskProject.task_id).label("task_count"),
        ).join(Task).where(Task.status != "done").group_by(TaskProject.project_id).subquery()

        # Get meeting counts per project
        meeting_count_subq = select(
            ProjectMeeting.project_id,
            func.count(ProjectMeeting.meeting_id).label("meeting_count"),
        ).group_by(ProjectMeeting.project_id).subquery()

        projects_query = select(
            Project,
            UserProject.role,
            UserProject.joined_at,
            func.coalesce(member_count_subq.c.member_count, 0).label("member_count"),
            func.coalesce(task_count_subq.c.task_count, 0).label("task_count"),
            func.coalesce(meeting_count_subq.c.meeting_count, 0).label("meeting_count"),
        ).join(UserProject).outerjoin(
            member_count_subq, Project.id == member_count_subq.c.project_id
        ).outerjoin(
            task_count_subq, Project.id == task_count_subq.c.project_id
        ).outerjoin(
            meeting_count_subq, Project.id == meeting_count_subq.c.project_id
        ).where(
            UserProject.user_id == self.user_id,
            Project.is_archived == False,
        ).order_by(desc(UserProject.joined_at)).limit(5)

        projects_results = self.db.exec(projects_query).all()

        formatted_projects = []
        for p, role, joined_at, member_count, task_count, meeting_count in projects_results:
            formatted_projects.append(QuickAccessProject(
                id=p.id,
                name=p.name,
                description=p.description,
                role=role,
                member_count=member_count,
                task_count=task_count,
                meeting_count=meeting_count,
                joined_at=joined_at,
            ))

        return QuickAccessData(
            upcoming_meetings=format_meetings(upcoming_meetings),
            recent_meetings=format_meetings(recent_meetings),
            priority_tasks=formatted_tasks,
            active_projects=formatted_projects,
        )

    def get_summary_stats(self, scope: DashboardScope) -> SummaryStats:
        """Get high-level summary statistics"""
        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(hours=24)

        # Task counts
        task_scope_filter = self._build_task_scope_filter(scope)
        task_query = select(
            func.count(Task.id).label("total"),
            func.sum(case((and_(Task.status != "done", or_(
                and_(Task.due_date < now, Task.due_date.isnot(None)),  # overdue
                and_(Task.due_date >= now, Task.due_date < tomorrow),  # due soon
            )), 1), else_=0)).label("pending"),
        ).where(task_scope_filter)
        task_result = self.db.exec(task_query).one()

        # Meeting counts
        meeting_scope_filter = self._build_meeting_scope_filter(scope)
        meeting_query = select(
            func.count(Meeting.id).label("total"),
            func.sum(case((and_(Meeting.start_time > now, Meeting.start_time < tomorrow), 1), else_=0)).label("upcoming_24h"),
        ).where(meeting_scope_filter, Meeting.is_deleted == False)
        meeting_result = self.db.exec(meeting_query).one()

        # Project count
        project_query = select(func.count(Project.id)).join(UserProject).where(
            UserProject.user_id == self.user_id,
            Project.is_archived == False,
        )
        project_count = self.db.exec(project_query).one() or 0

        return SummaryStats(
            total_tasks=task_result.total or 0,
            total_meetings=meeting_result.total or 0,
            total_projects=project_count,
            pending_tasks=task_result.pending or 0,
            upcoming_meetings_24h=meeting_result.upcoming_24h or 0,
        )

    def get_dashboard_stats(self, period: DashboardPeriod, scope: DashboardScope) -> DashboardResponse:
        """Get complete dashboard statistics"""
        start_date = self.get_date_range(period)

        return DashboardResponse(
            period=period,
            scope=scope,
            summary=self.get_summary_stats(scope),
            tasks=self.get_task_stats(start_date, scope),
            meetings=self.get_meeting_stats(start_date, scope),
            projects=self.get_project_stats(),
            storage=self.get_storage_stats(),
            quick_access=self.get_quick_access(),
        )
