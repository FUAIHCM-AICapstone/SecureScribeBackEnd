"""Unit tests for statistics service"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.schemas.statistics import DashboardPeriod, DashboardScope
from app.services.statistics import StatisticsService
from tests.factories import (
    AudioFileFactory,
    FileFactory,
    MeetingFactory,
    ProjectFactory,
    TaskFactory,
    UserFactory,
    UserProjectFactory,
)


class TestStatisticsService:
    """Tests for StatisticsService class"""

    def test_init(self, db_session: Session):
        """Test StatisticsService initialization"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        assert service.db == db_session
        assert service.user_id == user.id

    def test_get_date_range_seven_days(self, db_session: Session):
        """Test get_date_range for seven days period"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        result = service.get_date_range(DashboardPeriod.SEVEN_DAYS)
        expected = datetime.now(timezone.utc) - timedelta(days=7)

        assert result is not None
        # Allow small time difference
        assert abs((result - expected).total_seconds()) < 1

    def test_get_date_range_thirty_days(self, db_session: Session):
        """Test get_date_range for thirty days period"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        result = service.get_date_range(DashboardPeriod.THIRTY_DAYS)
        expected = datetime.now(timezone.utc) - timedelta(days=30)

        assert result is not None
        assert abs((result - expected).total_seconds()) < 1

    def test_get_date_range_ninety_days(self, db_session: Session):
        """Test get_date_range for ninety days period"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        result = service.get_date_range(DashboardPeriod.NINETY_DAYS)
        expected = datetime.now(timezone.utc) - timedelta(days=90)

        assert result is not None
        assert abs((result - expected).total_seconds()) < 1

    def test_get_date_range_all_time(self, db_session: Session):
        """Test get_date_range for all time period"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        result = service.get_date_range(None)
        assert result is None


class TestTaskStats:
    """Tests for get_task_stats method"""

    def test_get_task_stats_personal_scope(self, db_session: Session):
        """Test getting task stats for personal scope"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        # Create tasks assigned to user
        task1 = TaskFactory.create(db_session, user, status="todo")
        task2 = TaskFactory.create(db_session, user, status="in_progress")
        task3 = TaskFactory.create(db_session, user, status="done")
        db_session.commit()

        result = service.get_task_stats(None, DashboardScope.PERSONAL)

        assert result.total_assigned == 3
        assert result.todo_count == 1
        assert result.in_progress_count == 1
        assert result.done_count == 1
        assert result.completion_rate == 33.3  # 1/3 * 100

    def test_get_task_stats_project_scope(self, db_session: Session):
        """Test getting task stats for project scope"""
        user = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, user)
        service = StatisticsService(db_session, user.id)

        # Create tasks in user's projects
        task1 = TaskFactory.create(db_session, user, status="todo")
        task2 = TaskFactory.create(db_session, user, status="done")
        # Link tasks to project
        from app.models.task import TaskProject

        db_session.add(TaskProject(task_id=task1.id, project_id=project.id))
        db_session.add(TaskProject(task_id=task2.id, project_id=project.id))
        db_session.commit()

        result = service.get_task_stats(None, DashboardScope.PROJECT)

        assert result.total_assigned == 2
        assert result.done_count == 1
        assert result.completion_rate == 50.0

    def test_get_task_stats_with_date_filter(self, db_session: Session):
        """Test getting task stats with date filtering"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        # Create tasks with different dates
        old_date = datetime.now(timezone.utc) - timedelta(days=10)
        recent_date = datetime.now(timezone.utc) - timedelta(days=2)

        task1 = TaskFactory.create(db_session, user, status="done")
        task2 = TaskFactory.create(db_session, user, status="todo")

        # Manually set created_at dates
        task1.created_at = old_date
        task2.created_at = recent_date
        db_session.commit()

        # Filter for last 7 days
        start_date = datetime.now(timezone.utc) - timedelta(days=7)
        result = service.get_task_stats(start_date, DashboardScope.PERSONAL)

        # Should only include task2
        assert result.total_assigned == 1
        assert result.todo_count == 1

    def test_get_task_stats_overdue_count(self, db_session: Session):
        """Test overdue task counting"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        # Create overdue task
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        task = TaskFactory.create(db_session, user, status="todo", due_date=past_date)
        db_session.commit()

        result = service.get_task_stats(None, DashboardScope.PERSONAL)

        assert result.overdue_count == 1


class TestMeetingStats:
    """Tests for get_meeting_stats method"""

    def test_get_meeting_stats_personal_scope(self, db_session: Session):
        """Test getting meeting stats for personal scope"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        # Create meetings created by user
        meeting1 = MeetingFactory.create(db_session, user)
        meeting2 = MeetingFactory.create(db_session, user)
        db_session.commit()

        result = service.get_meeting_stats(None, DashboardScope.PERSONAL)

        assert result.total_count == 2

    def test_get_meeting_stats_project_scope(self, db_session: Session):
        """Test getting meeting stats for project scope"""
        user = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, user)
        service = StatisticsService(db_session, user.id)

        # Create meeting linked to user's project
        meeting = MeetingFactory.create(db_session, user)
        from app.models.meeting import ProjectMeeting

        db_session.add(ProjectMeeting(project_id=project.id, meeting_id=meeting.id))
        db_session.commit()

        result = service.get_meeting_stats(None, DashboardScope.PROJECT)

        assert result.total_count == 1

    def test_get_meeting_stats_with_duration(self, db_session: Session):
        """Test meeting stats with audio file duration"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        # Create meeting with audio file
        meeting = MeetingFactory.create(db_session, user)
        audio_file = AudioFileFactory.create(
            db_session,
            meeting=meeting,
            uploaded_by=user,
            duration_seconds=3600,  # 1 hour
        )
        db_session.commit()

        result = service.get_meeting_stats(None, DashboardScope.PERSONAL)

        assert result.total_count == 1
        assert result.total_duration_minutes == 60  # 3600 seconds = 60 minutes
        assert result.average_duration_minutes == 60.0

    def test_get_meeting_stats_bot_usage(self, db_session: Session):
        """Test meeting stats with bot usage"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        # Create meeting with bot
        meeting = MeetingFactory.create(db_session, user)
        from app.models.meeting import MeetingBot

        bot = MeetingBot(
            meeting_id=meeting.id,
            created_by=user.id,
            status="ended",  # Completed bot session
            meeting_url="https://meet.test.com",
        )
        db_session.add(bot)
        db_session.commit()

        result = service.get_meeting_stats(None, DashboardScope.PERSONAL)

        assert result.bot_usage_count == 1


class TestProjectStats:
    """Tests for get_project_stats method"""

    def test_get_project_stats(self, db_session: Session):
        """Test getting project statistics"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        # Create projects with different roles
        project1 = ProjectFactory.create(db_session, user)
        project2 = ProjectFactory.create(db_session, user)
        archived_project = ProjectFactory.create(db_session, user, is_archived=True)

        # Add user to projects with different roles
        UserProjectFactory.create(db_session, user, project1, role="admin")
        UserProjectFactory.create(db_session, user, project2, role="member")
        UserProjectFactory.create(db_session, user, archived_project, role="admin")
        db_session.commit()

        result = service.get_project_stats()

        assert result.total_active == 2
        assert result.total_archived == 1
        assert result.role_admin_count == 3  # owner + admin + owner + admin + owner
        assert result.role_member_count == 0


class TestStorageStats:
    """Tests for get_storage_stats method"""

    def test_get_storage_stats(self, db_session: Session):
        """Test getting storage statistics"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        # Create files with different sizes
        file1 = FileFactory.create(db_session, user, size_bytes=1024)  # 1KB
        file2 = FileFactory.create(db_session, user, size_bytes=2048)  # 2KB
        db_session.commit()

        result = service.get_storage_stats()

        assert result.total_files == 2
        assert result.total_size_bytes == 3072  # 1024 + 2048
        assert result.total_size_mb == 0.0  # 3072 / (1024*1024) ≈ 0.003, rounds to 0.0


class TestQuickAccess:
    """Tests for get_quick_access method"""

    def test_get_quick_access_upcoming_meetings(self, db_session: Session):
        """Test getting upcoming meetings in quick access"""
        user = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, user)
        service = StatisticsService(db_session, user.id)

        # Create upcoming meeting
        future_time = datetime.now(timezone.utc) + timedelta(hours=2)
        meeting = MeetingFactory.create(db_session, user)
        meeting.start_time = future_time

        # Link meeting to project
        from app.models.meeting import ProjectMeeting

        db_session.add(ProjectMeeting(project_id=project.id, meeting_id=meeting.id))
        db_session.commit()

        result = service.get_quick_access()

        assert len(result.upcoming_meetings) == 1
        assert result.upcoming_meetings[0].id == meeting.id

    def test_get_quick_access_recent_meetings(self, db_session: Session):
        """Test getting recent meetings in quick access"""
        user = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, user)
        service = StatisticsService(db_session, user.id)

        # Create past meeting
        past_time = datetime.now(timezone.utc) - timedelta(hours=2)
        meeting = MeetingFactory.create(db_session, user)
        meeting.start_time = past_time

        # Link meeting to project
        from app.models.meeting import ProjectMeeting

        db_session.add(ProjectMeeting(project_id=project.id, meeting_id=meeting.id))
        db_session.commit()

        result = service.get_quick_access()

        assert len(result.recent_meetings) == 1
        assert result.recent_meetings[0].id == meeting.id

    def test_get_quick_access_priority_tasks(self, db_session: Session):
        """Test getting priority tasks in quick access"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        # Create high priority overdue task
        past_date = datetime.now(timezone.utc) - timedelta(days=1)
        task = TaskFactory.create(db_session, user, title="Urgent Task", priority="Cao", due_date=past_date, status="todo")
        db_session.commit()

        result = service.get_quick_access()

        assert len(result.priority_tasks) == 1
        assert result.priority_tasks[0].id == task.id
        assert result.priority_tasks[0].title == "Urgent Task"

    def test_get_quick_access_active_projects(self, db_session: Session):
        """Test getting active projects in quick access"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        # Create active projects
        project1 = ProjectFactory.create(db_session, user, name="Project A")
        project2 = ProjectFactory.create(db_session, user, name="Project B")

        # Add user to projects
        UserProjectFactory.create(db_session, user, project1, role="admin")
        UserProjectFactory.create(db_session, user, project2, role="member")

        # Add another member to count members
        other_user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, other_user, project1, role="member")
        db_session.commit()

        result = service.get_quick_access()

        assert len(result.active_projects) == 2
        project_names = [p.name for p in result.active_projects]
        assert "Project A" in project_names
        assert "Project B" in project_names


class TestDashboardStats:
    """Tests for get_dashboard_stats method"""

    def test_get_dashboard_stats_all_periods(self, db_session: Session):
        """Test getting dashboard stats for all periods"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        # Create some test data
        task = TaskFactory.create(db_session, user, status="done")
        project = ProjectFactory.create(db_session, user)
        file_obj = FileFactory.create(db_session, user)
        db_session.commit()

        # Test different periods
        for period in [DashboardPeriod.SEVEN_DAYS, DashboardPeriod.THIRTY_DAYS, DashboardPeriod.NINETY_DAYS]:
            result = service.get_dashboard_stats(period, DashboardScope.PERSONAL)

            assert result.period == period
            assert result.scope == DashboardScope.PERSONAL
            assert hasattr(result, "tasks")
            assert hasattr(result, "meetings")
            assert hasattr(result, "projects")
            assert hasattr(result, "storage")
            assert hasattr(result, "quick_access")

    def test_get_dashboard_stats_all_time(self, db_session: Session):
        """Test getting dashboard stats for all time"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        result = service.get_dashboard_stats(DashboardPeriod.ALL_TIME, DashboardScope.PERSONAL)

        assert result.period == DashboardPeriod.ALL_TIME
        assert result.scope == DashboardScope.PERSONAL


class TestFillChartData:
    """Tests for _fill_chart_data method"""

    def test_fill_chart_data_with_date_range(self, db_session: Session):
        """Test filling chart data with date range"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        # Create test data
        base_date = datetime.now(timezone.utc).date()
        test_data = [
            (base_date, 5, 2),
            (base_date - timedelta(days=1), 3, 1),
        ]

        start_date = base_date - timedelta(days=7)
        result = service._fill_chart_data(test_data, start_date, DashboardPeriod.SEVEN_DAYS)

        # Should have 8 days (7 days + today)
        assert len(result) == 8

        # Check that existing data is preserved
        result_dates = [item.date for item in result]
        assert base_date in result_dates
        assert (base_date - timedelta(days=1)) in result_dates

    def test_fill_chart_data_without_date_range(self, db_session: Session):
        """Test filling chart data without date range (all time)"""
        user = UserFactory.create(db_session)
        service = StatisticsService(db_session, user.id)

        test_data = [
            (datetime(2024, 1, 1).date(), 5, 2),
            (datetime(2024, 1, 2).date(), 3, 1),
        ]

        result = service._fill_chart_data(test_data, None, DashboardPeriod.ALL_TIME)

        # Should return data as-is
        assert len(result) == 2
        assert result[0].date == datetime(2024, 1, 1).date()
        assert result[0].count == 5
        assert result[0].value == 2
