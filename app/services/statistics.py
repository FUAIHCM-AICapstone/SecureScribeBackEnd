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
        print(f"\033[34m[STATISTICS] Calculating date range for period: {period.value}\033[0m")
        now = datetime.now(timezone.utc)
        print(f"\033[34m[STATISTICS] Current UTC time: {now}\033[0m")
        if period == DashboardPeriod.SEVEN_DAYS:
            start_date = now - timedelta(days=7)
            print(f"\033[32m[STATISTICS] SEVEN_DAYS range: {start_date} to {now}\033[0m")
            return start_date
        elif period == DashboardPeriod.THIRTY_DAYS:
            start_date = now - timedelta(days=30)
            print(f"\033[32m[STATISTICS] THIRTY_DAYS range: {start_date} to {now}\033[0m")
            return start_date
        elif period == DashboardPeriod.NINETY_DAYS:
            start_date = now - timedelta(days=90)
            print(f"\033[32m[STATISTICS] NINETY_DAYS range: {start_date} to {now}\033[0m")
            return start_date
        print("\033[33m[STATISTICS] ALL_TIME period - no date range filter\033[0m")
        return None

    def _fill_chart_data(self, data: List[Any], start_date: Optional[datetime], period: DashboardPeriod) -> List[ChartDataPoint]:
        """Fill missing dates with zero values for charts"""
        print(f"\033[35m[STATISTICS] Filling chart data - {len(data)} data points, start_date: {start_date}, period: {period.value}\033[0m")
        if not start_date:
            # If 'all' time, just return what we have, or maybe limit to last 30 days for chart readability?
            # For 'all', let's just return the data we found sorted.
            result = [ChartDataPoint(date=d.date() if hasattr(d, "date") else d, count=c, value=v) for d, c, v in data]
            print(f"\033[33m[STATISTICS] ALL_TIME chart data: {len(result)} points processed\033[0m")
            return result

        # Create a map of existing data - convert datetime to date for keys
        data_map = {(d.date() if hasattr(d, "date") else d): (c, v) for d, c, v in data}
        print(f"\033[35m[STATISTICS] Created data map with {len(data_map)} entries\033[0m")

        result = []
        current_date = start_date.date() if hasattr(start_date, "date") else start_date
        end_date = datetime.now(timezone.utc).date()
        print(f"\033[35m[STATISTICS] Filling chart from {current_date} to {end_date}\033[0m")

        while current_date <= end_date:
            if current_date in data_map:
                count, value = data_map[current_date]
                result.append(ChartDataPoint(date=current_date, count=count, value=value))
                print(f"\033[32m[STATISTICS] Chart point {current_date}: count={count}, value={value} (from data)\033[0m")
            else:
                result.append(ChartDataPoint(date=current_date, count=0, value=0))
                print(f"\033[33m[STATISTICS] Chart point {current_date}: count=0, value=0 (filled)\033[0m")
            current_date += timedelta(days=1)

        print(f"\033[31m[STATISTICS] Chart data filled: {len(result)} total points\033[0m")
        return result

    def _build_task_scope_filter(self, scope: DashboardScope):
        """Build base filter conditions for task queries based on scope"""
        print(f"\033[36m[STATISTICS] Building task scope filter for user {self.user_id}, scope: {scope.value}\033[0m")
        if scope == DashboardScope.PROJECT:
            # Tasks in user's projects
            user_project_ids = select(UserProject.project_id).where(UserProject.user_id == self.user_id).scalar_subquery()
            task_ids_in_projects = select(TaskProject.task_id).where(TaskProject.project_id.in_(user_project_ids)).scalar_subquery()
            filter_condition = Task.id.in_(task_ids_in_projects)
            print("\033[32m[STATISTICS] PROJECT scope filter: Task.id.in_(task_ids from user's projects)\033[0m")
            return filter_condition
        else:
            # Personal or Hybrid: tasks assigned to or created by user
            filter_condition = or_(Task.assignee_id == self.user_id, Task.creator_id == self.user_id)
            print(f"\033[33m[STATISTICS] PERSONAL/HYBRID scope filter: Task.assignee_id == {self.user_id} OR Task.creator_id == {self.user_id}\033[0m")
            return filter_condition

    def get_task_stats(self, start_date: Optional[datetime], scope: DashboardScope) -> TaskStats:
        """Get task statistics with optimized single-pass aggregation query"""
        print(f"\033[35m[STATISTICS] Getting task stats for user {self.user_id}, scope: {scope.value}, start_date: {start_date}\033[0m")
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = today_start + timedelta(days=7)

        scope_filter = self._build_task_scope_filter(scope)
        print("\033[36m[STATISTICS] Task scope filter built, now calculating time ranges\033[0m")

        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = today_start + timedelta(days=7)
        print(f"\033[36m[STATISTICS] Time calculations: now={now}, today_start={today_start}, week_end={week_end}\033[0m")

        # Single aggregation query for all counts
        print("\033[34m[STATISTICS] Building main task aggregation query\033[0m")
        agg_query = select(
            func.count(Task.id).label("total"),
            func.sum(case((Task.status == "todo", 1), else_=0)).label("todo"),
            func.sum(case((Task.status == "in_progress", 1), else_=0)).label("in_progress"),
            func.sum(case((Task.status == "done", 1), else_=0)).label("done"),
            func.sum(case((and_(Task.status != "done", Task.due_date < now, Task.due_date.isnot(None)), 1), else_=0)).label("overdue"),
            func.sum(case((and_(Task.due_date >= today_start, Task.due_date < today_start + timedelta(days=1)), 1), else_=0)).label("due_today"),
            func.sum(case((and_(Task.due_date >= today_start, Task.due_date < week_end), 1), else_=0)).label("due_this_week"),
        ).where(scope_filter)
        print("\033[34m[STATISTICS] Task aggregation query built with scope filter\033[0m")

        result = self.db.exec(agg_query).one()
        total = result.total or 0
        todo = result.todo or 0
        in_progress = result.in_progress or 0
        done = result.done or 0
        overdue = result.overdue or 0
        due_today = result.due_today or 0
        due_this_week = result.due_this_week or 0
        print(f"\033[32m[STATISTICS] Task counts: total={total}, todo={todo}, in_progress={in_progress}, done={done}, overdue={overdue}, due_today={due_today}, due_this_week={due_this_week}\033[0m")

        # Period-specific counts
        created_in_period = 0
        completed_in_period = 0
        if start_date:
            print(f"\033[34m[STATISTICS] Building period-specific query for start_date: {start_date}\033[0m")
            period_query = select(
                func.count(Task.id).label("created"),
                func.sum(case((Task.status == "done", 1), else_=0)).label("completed"),
            ).where(scope_filter, Task.created_at >= start_date)
            period_result = self.db.exec(period_query).one()
            created_in_period = period_result.created or 0
            completed_in_period = period_result.completed or 0
            print(f"\033[32m[STATISTICS] Period counts: created={created_in_period}, completed={completed_in_period}\033[0m")

        # Completion rate
        rate = (done / total * 100) if total > 0 else 0.0
        print(f"\033[35m[STATISTICS] Completion rate calculation: {done}/{total} = {rate:.1f}%\033[0m")

        # Chart data: Tasks created per day with completed count as value
        print("\033[34m[STATISTICS] Building task chart data query\033[0m")
        date_col = func.date_trunc("day", Task.created_at).label("day")
        chart_query = select(
            date_col,
            func.count(Task.id).label("count"),
            func.sum(case((Task.status == "done", 1), else_=0)).label("completed"),
        ).where(scope_filter)

        if start_date:
            chart_query = chart_query.where(Task.created_at >= start_date)
            print(f"\033[34m[STATISTICS] Chart query filtered by start_date: {start_date}\033[0m")

        chart_query = chart_query.group_by(date_col).order_by(date_col)
        print("\033[34m[STATISTICS] Chart query built and grouped by day\033[0m")
        chart_results = self.db.exec(chart_query).all()
        print(f"\033[32m[STATISTICS] Chart query executed: {len(chart_results)} daily records\033[0m")

        formatted_chart_data = [(day, count, completed or 0) for day, count, completed in chart_results]
        print(f"\033[35m[STATISTICS] Chart data formatted: {len(formatted_chart_data)} points\033[0m")
        chart_data = self._fill_chart_data(formatted_chart_data, start_date, DashboardPeriod.ALL_TIME if not start_date else DashboardPeriod.SEVEN_DAYS)

        task_stats = TaskStats(
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
        print("\033[31m[STATISTICS] TaskStats object created and ready to return\033[0m")
        return task_stats

    def _build_meeting_scope_filter(self, scope: DashboardScope):
        """Build base filter for meeting queries based on scope"""
        print(f"\033[36m[STATISTICS] Building meeting scope filter for user {self.user_id}, scope: {scope.value}\033[0m")
        if scope == DashboardScope.PERSONAL:
            filter_condition = Meeting.created_by == self.user_id
            print(f"\033[33m[STATISTICS] PERSONAL scope filter: Meeting.created_by == {self.user_id}\033[0m")
            return filter_condition
        elif scope == DashboardScope.PROJECT:
            # Project scope: only meetings in user's projects
            user_project_ids = select(UserProject.project_id).where(UserProject.user_id == self.user_id).scalar_subquery()
            meeting_ids_in_projects = select(ProjectMeeting.meeting_id).where(ProjectMeeting.project_id.in_(user_project_ids)).scalar_subquery()
            filter_condition = Meeting.id.in_(meeting_ids_in_projects)
            print("\033[32m[STATISTICS] PROJECT scope filter: Meeting.id.in_(meeting_ids from user's projects)\033[0m")
            return filter_condition
        else:
            # Hybrid scope: personal meetings + project meetings
            user_project_ids = select(UserProject.project_id).where(UserProject.user_id == self.user_id).scalar_subquery()
            meeting_ids_in_projects = select(ProjectMeeting.meeting_id).where(ProjectMeeting.project_id.in_(user_project_ids)).scalar_subquery()
            filter_condition = or_(Meeting.created_by == self.user_id, Meeting.id.in_(meeting_ids_in_projects))
            print("\033[32m[STATISTICS] HYBRID scope filter: Personal + Project meetings\033[0m")
            return filter_condition

    def get_meeting_stats(self, start_date: Optional[datetime], scope: DashboardScope) -> MeetingStats:
        """Get meeting statistics with optimized queries"""
        print(f"\033[35m[STATISTICS] Getting meeting stats for user {self.user_id}, scope: {scope.value}, start_date: {start_date}\033[0m")
        now = datetime.now(timezone.utc)
        scope_filter = self._build_meeting_scope_filter(scope)
        print("\033[36m[STATISTICS] Meeting scope filter built, now building subqueries\033[0m")

        # Build meeting IDs subquery for reuse
        print("\033[34m[STATISTICS] Building meeting IDs subquery for reuse\033[0m")
        meeting_ids_subq = select(Meeting.id).where(scope_filter, Meeting.is_deleted == False)
        if start_date:
            meeting_ids_subq = meeting_ids_subq.where(Meeting.created_at >= start_date)
            print(f"\033[34m[STATISTICS] Meeting IDs subquery filtered by start_date: {start_date}\033[0m")
        meeting_ids_scalar = meeting_ids_subq.scalar_subquery()
        print("\033[34m[STATISTICS] Meeting IDs subquery built as scalar subquery\033[0m")

        # Single aggregation query for meeting counts
        print("\033[34m[STATISTICS] Building meeting count aggregation query\033[0m")
        count_query = select(
            func.count(func.distinct(Meeting.id)).label("total"),
        ).where(scope_filter, Meeting.is_deleted == False)
        if start_date:
            count_query = count_query.where(Meeting.created_at >= start_date)
            print(f"\033[34m[STATISTICS] Count query filtered by start_date: {start_date}\033[0m")
        total_count = self.db.exec(count_query).one() or 0
        print(f"\033[32m[STATISTICS] Total meetings count: {total_count}\033[0m")

        # Bot usage count - meetings with successful bot sessions
        print("\033[34m[STATISTICS] Building bot usage query\033[0m")
        bot_statuses = ["joined", "recording", "complete", "ended"]
        bot_query = select(func.count(func.distinct(MeetingBot.meeting_id))).where(
            MeetingBot.meeting_id.in_(meeting_ids_scalar),
            MeetingBot.status.in_(bot_statuses),
        )
        bot_usage = self.db.exec(bot_query).one() or 0
        print(f"\033[32m[STATISTICS] Bot usage count: {bot_usage} meetings\033[0m")

        # Meetings with transcripts
        print("\033[34m[STATISTICS] Building transcript query\033[0m")
        transcript_query = select(func.count(func.distinct(Transcript.meeting_id))).where(
            Transcript.meeting_id.in_(meeting_ids_scalar)
        )
        meetings_with_transcript = self.db.exec(transcript_query).one() or 0
        print(f"\033[32m[STATISTICS] Meetings with transcripts: {meetings_with_transcript}\033[0m")

        # Upcoming meetings count
        print("\033[34m[STATISTICS] Building upcoming meetings query\033[0m")
        upcoming_query = select(func.count(Meeting.id)).where(
            scope_filter,
            Meeting.is_deleted == False,
            Meeting.start_time > now,
            Meeting.status != MeetingStatus.cancelled,
        )
        upcoming_count = self.db.exec(upcoming_query).one() or 0
        print(f"\033[32m[STATISTICS] Upcoming meetings count: {upcoming_count}\033[0m")

        # Duration from AudioFiles
        print("\033[34m[STATISTICS] Building duration calculation query\033[0m")
        duration_query = select(func.sum(AudioFile.duration_seconds)).where(
            AudioFile.meeting_id.in_(meeting_ids_scalar),
            AudioFile.is_deleted == False,
        )
        total_seconds = self.db.exec(duration_query).one() or 0
        total_minutes = int(total_seconds / 60)
        avg_minutes = round(total_minutes / total_count, 1) if total_count > 0 else 0.0
        bot_usage_rate = round((bot_usage / total_count) * 100, 1) if total_count > 0 else 0.0
        print(f"\033[35m[STATISTICS] Duration calculations: {total_seconds}s = {total_minutes}min total, avg={avg_minutes}min, bot_rate={bot_usage_rate}%\033[0m")

        # Chart data: Meetings per day
        print("\033[34m[STATISTICS] Building meeting chart data query\033[0m")
        date_col = func.date_trunc("day", Meeting.created_at).label("day")
        chart_query = select(
            date_col,
            func.count(func.distinct(Meeting.id)).label("count"),
        ).where(scope_filter, Meeting.is_deleted == False)

        if start_date:
            chart_query = chart_query.where(Meeting.created_at >= start_date)
            print(f"\033[34m[STATISTICS] Meeting chart query filtered by start_date: {start_date}\033[0m")

        chart_query = chart_query.group_by(date_col).order_by(date_col)
        print("\033[34m[STATISTICS] Meeting chart query built and grouped by day\033[0m")
        chart_results = self.db.exec(chart_query).all()
        print(f"\033[32m[STATISTICS] Meeting chart query executed: {len(chart_results)} daily records\033[0m")

        formatted_chart_data = [(d, c, 0) for d, c in chart_results]
        print(f"\033[35m[STATISTICS] Meeting chart data formatted: {len(formatted_chart_data)} points\033[0m")
        period_for_chart = DashboardPeriod.ALL_TIME if not start_date else DashboardPeriod.SEVEN_DAYS
        chart_data = self._fill_chart_data(formatted_chart_data, start_date, period_for_chart)

        meeting_stats = MeetingStats(
            total_count=total_count,
            total_duration_minutes=total_minutes,
            average_duration_minutes=avg_minutes,
            bot_usage_count=bot_usage,
            bot_usage_rate=bot_usage_rate,
            meetings_with_transcript=meetings_with_transcript,
            upcoming_count=upcoming_count,
            chart_data=chart_data,
        )
        print("\033[31m[STATISTICS] MeetingStats object created and ready to return\033[0m")
        return meeting_stats

    def get_project_stats(self) -> ProjectStats:
        """Get project statistics with single aggregation query"""
        print(f"\033[35m[STATISTICS] Getting project stats for user {self.user_id}\033[0m")
        print("\033[34m[STATISTICS] Building project aggregation query\033[0m")
        query = select(
            func.count(Project.id).label("total"),
            func.sum(case((Project.is_archived == False, 1), else_=0)).label("active"),
            func.sum(case((Project.is_archived == True, 1), else_=0)).label("archived"),
            func.sum(case((UserProject.role.in_(["admin", "owner"]), 1), else_=0)).label("owned"),
            func.sum(case((UserProject.role == "member", 1), else_=0)).label("member"),
        ).select_from(Project).join(UserProject).where(UserProject.user_id == self.user_id)
        print("\033[34m[STATISTICS] Project aggregation query built\033[0m")

        result = self.db.exec(query).one()
        print(f"\033[32m[STATISTICS] Project query executed: total={result.total or 0}, active={result.active or 0}, archived={result.archived or 0}, owned={result.owned or 0}, member={result.member or 0}\033[0m")

        project_stats = ProjectStats(
            total_count=result.total or 0,
            active_count=result.active or 0,
            archived_count=result.archived or 0,
            owned_count=result.owned or 0,
            member_count=result.member or 0,
        )
        print("\033[31m[STATISTICS] ProjectStats object created and ready to return\033[0m")
        return project_stats

    def get_storage_stats(self) -> StorageStats:
        """Get storage statistics with file type breakdown"""
        print(f"\033[35m[STATISTICS] Getting storage stats for user {self.user_id}\033[0m")

        # Main aggregation
        print("\033[34m[STATISTICS] Building main storage aggregation query\033[0m")
        query = select(
            func.count(File.id).label("count"),
            func.coalesce(func.sum(File.size_bytes), 0).label("size_bytes"),
        ).where(File.uploaded_by == self.user_id)
        result = self.db.exec(query).one()
        print("\033[34m[STATISTICS] Main storage query executed\033[0m")

        count = result.count or 0
        size_bytes = result.size_bytes or 0
        size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes else 0.0
        print(f"\033[32m[STATISTICS] Storage calculations: {count} files, {size_bytes} bytes = {size_mb} MB\033[0m")

        # File type breakdown (top MIME types)
        print("\033[34m[STATISTICS] Building file type breakdown query\033[0m")
        type_query = select(
            File.mime_type,
            func.count(File.id).label("count"),
        ).where(
            File.uploaded_by == self.user_id,
            File.mime_type.isnot(None),
        ).group_by(File.mime_type).order_by(desc(func.count(File.id))).limit(10)

        type_results = self.db.exec(type_query).all()
        files_by_type = {mime: cnt for mime, cnt in type_results if mime}
        print(f"\033[32m[STATISTICS] File type breakdown: {len(files_by_type)} types found\033[0m")
        for mime_type, file_count in files_by_type.items():
            print(f"\033[32m[STATISTICS]   {mime_type}: {file_count} files\033[0m")

        storage_stats = StorageStats(
            total_files=count,
            total_size_bytes=size_bytes,
            total_size_mb=size_mb,
            files_by_type=files_by_type,
        )
        print("\033[31m[STATISTICS] StorageStats object created and ready to return\033[0m")
        return storage_stats

    def get_quick_access(self) -> QuickAccessData:
        """Get quick access data with optimized queries"""
        print(f"\033[35m[STATISTICS] Getting quick access data for user {self.user_id}\033[0m")
        now = datetime.now(timezone.utc)
        print(f"\033[36m[STATISTICS] Current time for quick access: {now}\033[0m")

        # Get user's project IDs once
        print("\033[34m[STATISTICS] Building user project IDs subquery\033[0m")
        user_project_ids = select(UserProject.project_id).where(UserProject.user_id == self.user_id).scalar_subquery()
        meeting_ids_in_projects = select(ProjectMeeting.meeting_id).where(ProjectMeeting.project_id.in_(user_project_ids)).scalar_subquery()
        print("\033[34m[STATISTICS] User project and meeting subqueries built\033[0m")

        # 1. Upcoming Meetings (Next 5) - Include both personal and project meetings
        print("\033[34m[STATISTICS] Building upcoming meetings query\033[0m")
        upcoming_query = select(Meeting).where(
            or_(Meeting.created_by == self.user_id, Meeting.id.in_(meeting_ids_in_projects)),
            Meeting.start_time > now,
            Meeting.status != MeetingStatus.cancelled,
            Meeting.is_deleted == False,
        ).order_by(Meeting.start_time).limit(5)
        upcoming_meetings = self.db.exec(upcoming_query).all()
        print(f"\033[32m[STATISTICS] Upcoming meetings query executed: {len(upcoming_meetings)} meetings\033[0m")

        # 2. Recent Meetings (Last 5) - Include both personal and project meetings
        print("\033[34m[STATISTICS] Building recent meetings query\033[0m")
        recent_query = select(Meeting).where(
            or_(Meeting.created_by == self.user_id, Meeting.id.in_(meeting_ids_in_projects)),
            Meeting.start_time < now,
            Meeting.is_deleted == False,
        ).order_by(desc(Meeting.start_time)).limit(5)
        recent_meetings = self.db.exec(recent_query).all()
        print(f"\033[32m[STATISTICS] Recent meetings query executed: {len(recent_meetings)} meetings\033[0m")

        def format_meetings(meetings: List[Meeting]) -> List[QuickAccessMeeting]:
            print(f"\033[35m[STATISTICS] Formatting {len(meetings)} meetings\033[0m")
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
                print(f"\033[35m[STATISTICS] Formatted meeting: {m.title} (projects: {len(project_names)}, transcript: {bool(m.transcript)}, recording: {has_recording})\033[0m")
            return result

        # 3. Priority Tasks (Overdue first, then by due date)
        print("\033[34m[STATISTICS] Building priority tasks query\033[0m")
        tasks_query = select(Task).where(
            or_(Task.assignee_id == self.user_id, Task.creator_id == self.user_id),
            Task.status != "done",
        ).order_by(
            # Overdue tasks first
            case((and_(Task.due_date < now, Task.due_date.isnot(None)), 0), else_=1),
            Task.due_date.asc().nulls_last(),
        ).limit(5)
        tasks = self.db.exec(tasks_query).all()
        print(f"\033[32m[STATISTICS] Priority tasks query executed: {len(tasks)} tasks\033[0m")

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
            print(f"\033[35m[STATISTICS] Formatted task: {t.title} (overdue: {is_overdue}, projects: {len(project_names)})\033[0m")

        # 4. Active Projects with counts (using subqueries for efficiency)
        print("\033[34m[STATISTICS] Building active projects queries with subqueries\033[0m")
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
        print(f"\033[32m[STATISTICS] Active projects query executed: {len(projects_results)} projects\033[0m")

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
            print(f"\033[35m[STATISTICS] Formatted project: {p.name} (role: {role}, members: {member_count}, tasks: {task_count}, meetings: {meeting_count})\033[0m")

        quick_access_data = QuickAccessData(
            upcoming_meetings=format_meetings(upcoming_meetings),
            recent_meetings=format_meetings(recent_meetings),
            priority_tasks=formatted_tasks,
            active_projects=formatted_projects,
        )
        print("\033[31m[STATISTICS] QuickAccessData object created and ready to return\033[0m")
        return quick_access_data

    def get_summary_stats(self, scope: DashboardScope) -> SummaryStats:
        """Get high-level summary statistics"""
        print(f"\033[35m[STATISTICS] Getting summary stats for user {self.user_id}, scope: {scope.value}\033[0m")
        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(hours=24)

        # Task counts
        print("\033[34m[STATISTICS] Building task summary query\033[0m")
        task_scope_filter = self._build_task_scope_filter(scope)
        task_query = select(
            func.count(Task.id).label("total"),
            func.sum(case((and_(Task.status != "done", or_(
                and_(Task.due_date < now, Task.due_date.isnot(None)),  # overdue
                and_(Task.due_date >= now, Task.due_date < tomorrow),  # due soon
            )), 1), else_=0)).label("pending"),
        ).where(task_scope_filter)
        task_result = self.db.exec(task_query).one()
        print(f"\033[32m[STATISTICS] Task summary: total={task_result.total or 0}, pending={task_result.pending or 0}\033[0m")

        # Meeting counts
        print("\033[34m[STATISTICS] Building meeting summary query\033[0m")
        meeting_scope_filter = self._build_meeting_scope_filter(scope)
        meeting_query = select(
            func.count(Meeting.id).label("total"),
            func.sum(case((and_(Meeting.start_time > now, Meeting.start_time < tomorrow), 1), else_=0)).label("upcoming_24h"),
        ).where(meeting_scope_filter, Meeting.is_deleted == False)
        meeting_result = self.db.exec(meeting_query).one()
        print(f"\033[32m[STATISTICS] Meeting summary: total={meeting_result.total or 0}, upcoming_24h={meeting_result.upcoming_24h or 0}\033[0m")

        # Project count
        print("\033[34m[STATISTICS] Building project summary query\033[0m")
        project_query = select(func.count(Project.id)).join(UserProject).where(
            UserProject.user_id == self.user_id,
            Project.is_archived == False,
        )
        project_count = self.db.exec(project_query).one() or 0
        print(f"\033[32m[STATISTICS] Project summary: active_projects={project_count}\033[0m")

        summary_stats = SummaryStats(
            total_tasks=task_result.total or 0,
            total_meetings=meeting_result.total or 0,
            total_projects=project_count,
            pending_tasks=task_result.pending or 0,
            upcoming_meetings_24h=meeting_result.upcoming_24h or 0,
        )
        print("\033[31m[STATISTICS] SummaryStats object created and ready to return\033[0m")
        return summary_stats

    def get_dashboard_stats(self, period: DashboardPeriod, scope: DashboardScope) -> DashboardResponse:
        """Get complete dashboard statistics"""
        print(f"\033[31m[STATISTICS] Getting dashboard stats for user {self.user_id}, period: {period.value}, scope: {scope.value}\033[0m")
        start_date = self.get_date_range(period)
        print(f"\033[36m[STATISTICS] Date range calculated: {start_date}\033[0m")

        print("\033[35m[STATISTICS] Calling get_summary_stats\033[0m")
        summary = self.get_summary_stats(scope)

        print("\033[35m[STATISTICS] Calling get_task_stats\033[0m")
        tasks = self.get_task_stats(start_date, scope)

        print("\033[35m[STATISTICS] Calling get_meeting_stats\033[0m")
        meetings = self.get_meeting_stats(start_date, scope)

        print("\033[35m[STATISTICS] Calling get_project_stats\033[0m")
        projects = self.get_project_stats()

        print("\033[35m[STATISTICS] Calling get_storage_stats\033[0m")
        storage = self.get_storage_stats()

        print("\033[35m[STATISTICS] Calling get_quick_access\033[0m")
        quick_access = self.get_quick_access()

        dashboard_response = DashboardResponse(
            period=period,
            scope=scope,
            summary=summary,
            tasks=tasks,
            meetings=meetings,
            projects=projects,
            storage=storage,
            quick_access=quick_access,
        )
        print("\033[31m[STATISTICS] DashboardResponse object created with all stats and ready to return\033[0m")
        return dashboard_response
