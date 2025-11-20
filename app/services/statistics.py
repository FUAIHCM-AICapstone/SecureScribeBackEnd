from datetime import datetime, timedelta
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import case, desc, func, or_
from sqlmodel import Session, col, select

from app.models.file import File
from app.models.meeting import AudioFile, Meeting, MeetingBot, MeetingStatus, ProjectMeeting
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
    TaskStats,
)


class StatisticsService:
    def __init__(self, db: Session, user_id: UUID):
        self.db = db
        self.user_id = user_id

    def get_date_range(self, period: DashboardPeriod) -> Optional[datetime]:
        now = datetime.utcnow()
        if period == DashboardPeriod.SEVEN_DAYS:
            return now - timedelta(days=7)
        elif period == DashboardPeriod.THIRTY_DAYS:
            return now - timedelta(days=30)
        elif period == DashboardPeriod.NINETY_DAYS:
            return now - timedelta(days=90)
        return None

    def _fill_chart_data(
        self, data: List[Any], start_date: Optional[datetime], period: DashboardPeriod
    ) -> List[ChartDataPoint]:
        """Fill missing dates with zero values for charts"""
        if not start_date:
            # If 'all' time, just return what we have, or maybe limit to last 30 days for chart readability?
            # For 'all', let's just return the data we found sorted.
            return [
                ChartDataPoint(date=d.day, count=c, value=v) for d, c, v in data
            ]

        # Create a map of existing data
        data_map = {d.day: (c, v) for d, c, v in data}

        result = []
        current_date = start_date.date()
        end_date = datetime.utcnow().date()

        while current_date <= end_date:
            if current_date in data_map:
                count, value = data_map[current_date]
                result.append(ChartDataPoint(date=current_date, count=count, value=value))
            else:
                result.append(ChartDataPoint(date=current_date, count=0, value=0))
            current_date += timedelta(days=1)

        return result

    def get_task_stats(self, start_date: Optional[datetime], scope: DashboardScope) -> TaskStats:
        # Determine filter based on scope
        # Hybrid/Personal: Tasks assigned to user
        # Project: Tasks in user's projects (regardless of assignee)

        query = select(Task)

        if scope == DashboardScope.PROJECT:
            # Join with projects user is in
            query = query.join(TaskProject).join(UserProject, TaskProject.project_id == UserProject.project_id)
            query = query.where(UserProject.user_id == self.user_id)
        else:
            # Personal or Hybrid (default for tasks is personal)
            query = query.where(Task.assignee_id == self.user_id)

        if start_date:
            query = query.where(Task.created_at >= start_date)

        # Execute main query to get objects for status counting
        # For performance on large datasets, we should use aggregation queries
        # But for now, let's use aggregation functions

        # Status counts
        status_query = select(
            Task.status, func.count(Task.id)
        ).select_from(Task)

        if scope == DashboardScope.PROJECT:
            status_query = status_query.join(TaskProject).join(UserProject, TaskProject.project_id == UserProject.project_id)
            status_query = status_query.where(UserProject.user_id == self.user_id)
        else:
            status_query = status_query.where(Task.assignee_id == self.user_id)

        if start_date:
            status_query = status_query.where(Task.created_at >= start_date)

        status_query = status_query.group_by(Task.status)
        status_results = self.db.exec(status_query).all()

        status_map = dict(status_results)
        todo = status_map.get("todo", 0)
        in_progress = status_map.get("in_progress", 0)
        done = status_map.get("done", 0)
        total = todo + in_progress + done

        # Overdue count (only active tasks)
        overdue_query = select(func.count(Task.id)).where(
            Task.status != "done",
            Task.due_date < datetime.utcnow()
        )
        if scope == DashboardScope.PROJECT:
            overdue_query = overdue_query.join(TaskProject).join(UserProject, TaskProject.project_id == UserProject.project_id)
            overdue_query = overdue_query.where(UserProject.user_id == self.user_id)
        else:
            overdue_query = overdue_query.where(Task.assignee_id == self.user_id)

        overdue = self.db.exec(overdue_query).one() or 0

        # Completion rate
        rate = (done / total * 100) if total > 0 else 0.0

        # Chart data: Tasks created per day
        # We could also do tasks completed per day, but let's stick to created for activity
        date_col = func.date_trunc('day', Task.created_at).label('day')
        chart_query = select(
            date_col,
            func.count(Task.id),
            func.sum(case((Task.status == 'done', 1), else_=0)) # Value can be completed count
        )

        if scope == DashboardScope.PROJECT:
            chart_query = chart_query.join(TaskProject).join(UserProject, TaskProject.project_id == UserProject.project_id)
            chart_query = chart_query.where(UserProject.user_id == self.user_id)
        else:
            chart_query = chart_query.where(Task.assignee_id == self.user_id)

        if start_date:
            chart_query = chart_query.where(Task.created_at >= start_date)

        chart_query = chart_query.group_by(date_col).order_by(date_col)
        chart_results = self.db.exec(chart_query).all()

        # Format chart data
        # result tuple: (datetime, count_created, count_done)
        formatted_chart_data = []
        for day, created, completed in chart_results:
            formatted_chart_data.append((day, created, completed))

        # Fill gaps if we have a start date
        # Note: _fill_chart_data expects (date, count, value)
        chart_data = self._fill_chart_data(formatted_chart_data, start_date, DashboardPeriod.ALL_TIME if not start_date else DashboardPeriod.SEVEN_DAYS) # Period enum is just for logic

        return TaskStats(
            total_assigned=total,
            todo_count=todo,
            in_progress_count=in_progress,
            done_count=done,
            overdue_count=overdue,
            completion_rate=round(rate, 1),
            chart_data=chart_data
        )

    def get_meeting_stats(self, start_date: Optional[datetime], scope: DashboardScope) -> MeetingStats:
        # Hybrid/Project: Meetings in user's projects
        # Personal: Meetings created by user

        base_query = select(Meeting)

        if scope == DashboardScope.PERSONAL:
            base_query = base_query.where(Meeting.created_by == self.user_id)
        else:
            # Hybrid or Project
            base_query = base_query.join(ProjectMeeting).join(UserProject, ProjectMeeting.project_id == UserProject.project_id)
            base_query = base_query.where(UserProject.user_id == self.user_id).distinct()

        if start_date:
            base_query = base_query.where(Meeting.created_at >= start_date)

        # Total count
        count_query = select(func.count(col(Meeting.id))).select_from(base_query.subquery())
        total_count = self.db.exec(count_query).one() or 0

        # Bot usage (meetings with bot status 'ended' or 'joined')
        bot_query = base_query.join(MeetingBot).where(
            or_(MeetingBot.status == "ended", MeetingBot.status == "joined")
        )
        # We need to count distinct meetings because of joins
        bot_count_query = select(func.count(func.distinct(Meeting.id))).select_from(bot_query.subquery())
        bot_usage = self.db.exec(bot_count_query).one() or 0

        # Duration calculation
        # Sum duration from AudioFiles linked to these meetings
        # We need to be careful with the join structure for aggregation

        # Let's get the meeting IDs first to simplify duration query if dataset is not huge
        # Or use a subquery

        meeting_ids_query = select(Meeting.id)
        if scope == DashboardScope.PERSONAL:
            meeting_ids_query = meeting_ids_query.where(Meeting.created_by == self.user_id)
        else:
            meeting_ids_query = meeting_ids_query.join(ProjectMeeting).join(UserProject, ProjectMeeting.project_id == UserProject.project_id)
            meeting_ids_query = meeting_ids_query.where(UserProject.user_id == self.user_id)

        if start_date:
            meeting_ids_query = meeting_ids_query.where(Meeting.created_at >= start_date)

        # Duration from AudioFiles
        duration_query = select(func.sum(AudioFile.duration_seconds)).where(
            AudioFile.meeting_id.in_(meeting_ids_query)
        )
        total_seconds = self.db.exec(duration_query).one() or 0
        total_minutes = int(total_seconds / 60)
        avg_minutes = round(total_minutes / total_count, 1) if total_count > 0 else 0.0

        # Chart data: Meetings per day + Duration per day
        date_col = func.date_trunc('day', Meeting.created_at).label('day')

        # We need to join AudioFile to get duration per day, but grouping by meeting creation date
        # This is complex in one query. Let's just count meetings per day for now,
        # and maybe approximate duration or fetch separately.
        # Let's do: Count meetings per day.

        chart_query = select(
            date_col,
            func.count(func.distinct(Meeting.id)),
            func.sum(0) # Placeholder for duration in this query
        )

        if scope == DashboardScope.PERSONAL:
            chart_query = chart_query.where(Meeting.created_by == self.user_id)
        else:
            chart_query = chart_query.join(ProjectMeeting).join(UserProject, ProjectMeeting.project_id == UserProject.project_id)
            chart_query = chart_query.where(UserProject.user_id == self.user_id)

        if start_date:
            chart_query = chart_query.where(Meeting.created_at >= start_date)

        chart_query = chart_query.group_by(date_col).order_by(date_col)
        chart_results = self.db.exec(chart_query).all()

        formatted_chart_data = [(d, c, 0) for d, c, _ in chart_results]
        chart_data = self._fill_chart_data(formatted_chart_data, start_date, DashboardPeriod.ALL_TIME)

        return MeetingStats(
            total_count=total_count,
            total_duration_minutes=total_minutes,
            average_duration_minutes=avg_minutes,
            bot_usage_count=bot_usage,
            chart_data=chart_data
        )

    def get_project_stats(self) -> ProjectStats:
        # Always project scope effectively
        query = select(Project, UserProject.role).join(UserProject).where(UserProject.user_id == self.user_id)
        results = self.db.exec(query).all()

        total_active = 0
        total_archived = 0
        role_admin = 0
        role_member = 0

        for project, role in results:
            if project.is_archived:
                total_archived += 1
            else:
                total_active += 1

            if role == "admin" or role == "owner": # Assuming 'owner' is also admin-like
                role_admin += 1
            else:
                role_member += 1

        return ProjectStats(
            total_active=total_active,
            total_archived=total_archived,
            role_admin_count=role_admin,
            role_member_count=role_member
        )

    def get_storage_stats(self) -> StorageStats:
        # Personal uploads
        query = select(func.count(File.id), func.sum(File.size_bytes)).where(
            File.uploaded_by == self.user_id
        )
        count, size_bytes = self.db.exec(query).one()

        count = count or 0
        size_bytes = size_bytes or 0
        size_mb = round(size_bytes / (1024 * 1024), 2)

        return StorageStats(
            total_files=count,
            total_size_bytes=size_bytes,
            total_size_mb=size_mb
        )

    def get_quick_access(self) -> QuickAccessData:
        # 1. Upcoming Meetings (Next 5)
        upcoming_query = select(Meeting).join(ProjectMeeting).join(UserProject, ProjectMeeting.project_id == UserProject.project_id)
        upcoming_query = upcoming_query.where(
            UserProject.user_id == self.user_id,
            Meeting.start_time > datetime.utcnow(),
            Meeting.status != MeetingStatus.cancelled
        ).distinct().order_by(Meeting.start_time).limit(5)

        upcoming_meetings = self.db.exec(upcoming_query).all()

        # 2. Recent Meetings (Last 5 completed)
        recent_query = select(Meeting).join(ProjectMeeting).join(UserProject, ProjectMeeting.project_id == UserProject.project_id)
        recent_query = recent_query.where(
            UserProject.user_id == self.user_id,
            Meeting.start_time < datetime.utcnow()
        ).distinct().order_by(desc(Meeting.start_time)).limit(5)

        recent_meetings = self.db.exec(recent_query).all()

        # Helper to format meetings
        def format_meetings(meetings: List[Meeting]) -> List[QuickAccessMeeting]:
            result = []
            for m in meetings:
                # Get project name (first one)
                project_name = None
                if m.projects:
                    project_name = m.projects[0].project.name

                result.append(QuickAccessMeeting(
                    id=m.id,
                    title=m.title,
                    start_time=m.start_time,
                    end_time=None, # Not in Meeting model directly, would need Bot or Audio calc
                    url=m.url,
                    project_name=project_name,
                    status=m.status,
                    has_transcript=bool(m.transcript)
                ))
            return result

        # 3. Priority Tasks (Overdue or High Priority, limit 5)
        # Sort by: Overdue first (due_date asc), then Priority, then Created
        tasks_query = select(Task).where(
            Task.assignee_id == self.user_id,
            Task.status != "done"
        ).order_by(Task.due_date.asc().nulls_last(), desc(Task.priority)).limit(5)

        tasks = self.db.exec(tasks_query).all()

        formatted_tasks = []
        for t in tasks:
            # Get project name
            project_name = None
            # Need to fetch projects for task
            # This might trigger lazy load or we can join.
            # Since we are in a session, lazy load is fine for small limit.
            if t.projects:
                project_name = t.projects[0].project.name

            formatted_tasks.append(QuickAccessTask(
                id=t.id,
                title=t.title,
                due_date=t.due_date,
                priority=t.priority,
                status=t.status,
                project_name=project_name
            ))

        # 4. Active Projects (Top 5 by join date desc)
        projects_query = select(Project, UserProject).join(UserProject).where(
            UserProject.user_id == self.user_id,
            Project.is_archived == False
        ).order_by(desc(UserProject.joined_at)).limit(5)

        projects = self.db.exec(projects_query).all()

        formatted_projects = []
        for p, up in projects:
            # Count members - separate query or subquery
            member_count = self.db.exec(select(func.count(UserProject.user_id)).where(UserProject.project_id == p.id)).one()

            formatted_projects.append(QuickAccessProject(
                id=p.id,
                name=p.name,
                role=up.role,
                member_count=member_count,
                joined_at=up.joined_at
            ))

        return QuickAccessData(
            upcoming_meetings=format_meetings(upcoming_meetings),
            recent_meetings=format_meetings(recent_meetings),
            priority_tasks=formatted_tasks,
            active_projects=formatted_projects
        )

    def get_dashboard_stats(self, period: DashboardPeriod, scope: DashboardScope) -> DashboardResponse:
        start_date = self.get_date_range(period)

        return DashboardResponse(
            period=period,
            scope=scope,
            tasks=self.get_task_stats(start_date, scope),
            meetings=self.get_meeting_stats(start_date, scope),
            projects=self.get_project_stats(),
            storage=self.get_storage_stats(),
            quick_access=self.get_quick_access()
        )
