"""Unit tests for meeting bot service functions"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from faker import Faker
from sqlalchemy.orm import Session

from app.models.meeting import MeetingBot, MeetingBotLog
from app.schemas.meeting_bot import MeetingBotCreate, MeetingBotLogCreate, MeetingBotUpdate
from app.services.meeting_bot import (
    create_bot_log,
    create_meeting_bot,
    delete_meeting_bot,
    get_bot_logs,
    get_meeting_bot,
    get_meeting_bot_by_meeting,
    get_meeting_bots,
    update_bot_status,
    update_meeting_bot,
)
from tests.factories import MeetingBotFactory, MeetingFactory, UserFactory

fake = Faker()


class TestCreateMeetingBot:
    """Tests for create_meeting_bot function"""

    def test_create_meeting_bot_success(self, db_session: Session):
        """Test creating a meeting bot with valid data"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot_data = MeetingBotCreate(
            meeting_id=meeting.id,
            scheduled_start_time=datetime.now(timezone.utc) + timedelta(hours=1),
            meeting_url="https://zoom.us/j/123456",
        )

        bot = create_meeting_bot(db_session, bot_data, creator.id)

        assert bot.id is not None
        assert bot.meeting_id == meeting.id
        assert bot.created_by == creator.id
        assert bot.status == "pending"
        assert bot.meeting_url == "https://zoom.us/j/123456"
        assert bot.scheduled_start_time is not None

    def test_create_meeting_bot_meeting_not_found(self, db_session: Session):
        """Test creating bot for non-existent meeting"""
        creator = UserFactory.create(db_session)
        fake_meeting_id = uuid.uuid4()
        bot_data = MeetingBotCreate(meeting_id=fake_meeting_id)

        with pytest.raises(Exception):  # HTTPException
            create_meeting_bot(db_session, bot_data, creator.id)

    def test_create_meeting_bot_already_exists(self, db_session: Session):
        """Test creating bot when one already exists for meeting"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        MeetingBotFactory.create(db_session, meeting, creator)

        bot_data = MeetingBotCreate(meeting_id=meeting.id)

        with pytest.raises(Exception):  # HTTPException
            create_meeting_bot(db_session, bot_data, creator.id)

    def test_create_meeting_bot_with_scheduled_time(self, db_session: Session):
        """Test creating bot with scheduled start time"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        scheduled_time = datetime.now(timezone.utc) + timedelta(hours=2)
        bot_data = MeetingBotCreate(
            meeting_id=meeting.id,
            scheduled_start_time=scheduled_time,
        )

        bot = create_meeting_bot(db_session, bot_data, creator.id)

        assert bot.scheduled_start_time == scheduled_time

    def test_create_meeting_bot_timestamps(self, db_session: Session):
        """Test that bot has correct timestamps"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot_data = MeetingBotCreate(meeting_id=meeting.id)
        before_creation = datetime.now(timezone.utc)

        bot = create_meeting_bot(db_session, bot_data, creator.id)

        assert bot.created_at is not None
        assert bot.created_at >= before_creation


class TestGetMeetingBot:
    """Tests for get_meeting_bot function"""

    def test_get_meeting_bot_success(self, db_session: Session):
        """Test getting a meeting bot by ID"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)

        retrieved_bot = get_meeting_bot(db_session, bot.id, creator.id)

        assert retrieved_bot is not None
        assert retrieved_bot.id == bot.id
        assert retrieved_bot.meeting_id == meeting.id

    def test_get_meeting_bot_not_found(self, db_session: Session):
        """Test getting non-existent bot"""
        creator = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        bot = get_meeting_bot(db_session, fake_id, creator.id)

        assert bot is None

    def test_get_meeting_bot_with_logs(self, db_session: Session):
        """Test getting bot includes logs"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        log_data = MeetingBotLogCreate(action="joined", message="Bot joined meeting")
        create_bot_log(db_session, bot.id, log_data)

        retrieved_bot = get_meeting_bot(db_session, bot.id, creator.id)

        assert retrieved_bot is not None
        assert len(retrieved_bot.logs) > 0
        assert retrieved_bot.logs[0].action == "joined"

    def test_get_meeting_bot_with_meeting_data(self, db_session: Session):
        """Test getting bot includes meeting data"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, title="Test Meeting")
        bot = MeetingBotFactory.create(db_session, meeting, creator)

        retrieved_bot = get_meeting_bot(db_session, bot.id, creator.id)

        assert retrieved_bot is not None
        assert retrieved_bot.meeting is not None
        assert retrieved_bot.meeting.title == "Test Meeting"


class TestGetMeetingBotByMeeting:
    """Tests for get_meeting_bot_by_meeting function"""

    def test_get_meeting_bot_by_meeting_success(self, db_session: Session):
        """Test getting bot by meeting ID"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)

        retrieved_bot = get_meeting_bot_by_meeting(db_session, meeting.id, creator.id)

        assert retrieved_bot is not None
        assert retrieved_bot.id == bot.id
        assert retrieved_bot.meeting_id == meeting.id

    def test_get_meeting_bot_by_meeting_not_found(self, db_session: Session):
        """Test getting bot for meeting with no bot"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)

        bot = get_meeting_bot_by_meeting(db_session, meeting.id, creator.id)

        assert bot is None

    def test_get_meeting_bot_by_meeting_invalid_meeting(self, db_session: Session):
        """Test getting bot for non-existent meeting"""
        creator = UserFactory.create(db_session)
        fake_meeting_id = uuid.uuid4()

        bot = get_meeting_bot_by_meeting(db_session, fake_meeting_id, creator.id)

        assert bot is None


class TestGetMeetingBots:
    """Tests for get_meeting_bots function"""

    def test_get_meeting_bots_success(self, db_session: Session):
        """Test getting all bots for a user"""
        creator = UserFactory.create(db_session)
        meeting1 = MeetingFactory.create(db_session, creator)
        meeting2 = MeetingFactory.create(db_session, creator)
        bot1 = MeetingBotFactory.create(db_session, meeting1, creator)
        bot2 = MeetingBotFactory.create(db_session, meeting2, creator)

        bots, total = get_meeting_bots(db_session, creator.id)

        assert len(bots) >= 2
        assert total >= 2
        bot_ids = [b.id for b in bots]
        assert bot1.id in bot_ids
        assert bot2.id in bot_ids

    def test_get_meeting_bots_pagination(self, db_session: Session):
        """Test getting bots with pagination"""
        creator = UserFactory.create(db_session)
        for _ in range(5):
            meeting = MeetingFactory.create(db_session, creator)
            MeetingBotFactory.create(db_session, meeting, creator)

        bots, total = get_meeting_bots(db_session, creator.id, page=1, limit=2)

        assert len(bots) <= 2
        assert total >= 5

    def test_get_meeting_bots_page_2(self, db_session: Session):
        """Test getting second page of bots"""
        creator = UserFactory.create(db_session)
        for _ in range(5):
            meeting = MeetingFactory.create(db_session, creator)
            MeetingBotFactory.create(db_session, meeting, creator)

        page1_bots, total = get_meeting_bots(db_session, creator.id, page=1, limit=2)
        page2_bots, _ = get_meeting_bots(db_session, creator.id, page=2, limit=2)

        page1_ids = [b.id for b in page1_bots]
        page2_ids = [b.id for b in page2_bots]

        # Ensure pages don't overlap
        assert len(set(page1_ids) & set(page2_ids)) == 0

    def test_get_meeting_bots_only_user_bots(self, db_session: Session):
        """Test that only user's bots are returned"""
        creator1 = UserFactory.create(db_session)
        creator2 = UserFactory.create(db_session)
        meeting1 = MeetingFactory.create(db_session, creator1)
        meeting2 = MeetingFactory.create(db_session, creator2)
        bot1 = MeetingBotFactory.create(db_session, meeting1, creator1)
        MeetingBotFactory.create(db_session, meeting2, creator2)

        bots, total = get_meeting_bots(db_session, creator1.id)

        bot_ids = [b.id for b in bots]
        assert bot1.id in bot_ids
        # Should not include creator2's bots
        assert all(b.created_by == creator1.id for b in bots)

    def test_get_meeting_bots_logs_sorted(self, db_session: Session):
        """Test that logs are sorted by created_at descending"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)

        # Create logs with different timestamps
        log1 = create_bot_log(db_session, bot.id, MeetingBotLogCreate(action="action1"))
        log2 = create_bot_log(db_session, bot.id, MeetingBotLogCreate(action="action2"))

        bots, _ = get_meeting_bots(db_session, creator.id)
        retrieved_bot = bots[0]

        # Logs should be sorted descending by created_at
        assert retrieved_bot.logs[0].created_at >= retrieved_bot.logs[1].created_at

    def test_get_meeting_bots_empty_for_user(self, db_session: Session):
        """Test getting bots for user with no bots"""
        creator = UserFactory.create(db_session)

        bots, total = get_meeting_bots(db_session, creator.id)

        assert len(bots) == 0
        assert total == 0


class TestUpdateMeetingBot:
    """Tests for update_meeting_bot function"""

    def test_update_meeting_bot_success(self, db_session: Session):
        """Test updating a bot with valid data"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator, status="pending")
        updates = MeetingBotUpdate(status="joined")

        updated_bot = update_meeting_bot(db_session, bot.id, updates, creator.id)

        assert updated_bot is not None
        assert updated_bot.status == "joined"
        assert updated_bot.id == bot.id

    def test_update_meeting_bot_not_found(self, db_session: Session):
        """Test updating non-existent bot"""
        creator = UserFactory.create(db_session)
        fake_id = uuid.uuid4()
        updates = MeetingBotUpdate(status="joined")

        result = update_meeting_bot(db_session, fake_id, updates, creator.id)

        assert result is None

    def test_update_meeting_bot_unauthorized(self, db_session: Session):
        """Test non-creator cannot update bot"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        updates = MeetingBotUpdate(status="joined")

        with pytest.raises(Exception):  # HTTPException
            update_meeting_bot(db_session, bot.id, updates, other_user.id)

    def test_update_meeting_bot_partial_fields(self, db_session: Session):
        """Test updating only some fields"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(
            db_session,
            meeting,
            creator,
            status="pending",
            meeting_url="https://zoom.us/j/123",
        )
        updates = MeetingBotUpdate(status="joined")

        updated_bot = update_meeting_bot(db_session, bot.id, updates, creator.id)

        assert updated_bot.status == "joined"
        assert updated_bot.meeting_url == "https://zoom.us/j/123"

    def test_update_meeting_bot_meeting_url(self, db_session: Session):
        """Test updating meeting URL"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        new_url = "https://zoom.us/j/456"
        updates = MeetingBotUpdate(meeting_url=new_url)

        updated_bot = update_meeting_bot(db_session, bot.id, updates, creator.id)

        assert updated_bot.meeting_url == new_url

    def test_update_meeting_bot_timestamps(self, db_session: Session):
        """Test that updated_at is set"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        original_updated_at = bot.updated_at
        updates = MeetingBotUpdate(status="joined")

        updated_bot = update_meeting_bot(db_session, bot.id, updates, creator.id)

        assert updated_bot.updated_at is not None
        # updated_at should be more recent than original
        if original_updated_at:
            assert updated_bot.updated_at >= original_updated_at

    def test_update_meeting_bot_actual_times(self, db_session: Session):
        """Test updating actual start and end times"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        start_time = datetime.now(timezone.utc)
        end_time = datetime.now(timezone.utc) + timedelta(hours=1)
        updates = MeetingBotUpdate(
            actual_start_time=start_time,
            actual_end_time=end_time,
        )

        updated_bot = update_meeting_bot(db_session, bot.id, updates, creator.id)

        assert updated_bot.actual_start_time == start_time
        assert updated_bot.actual_end_time == end_time


class TestDeleteMeetingBot:
    """Tests for delete_meeting_bot function"""

    def test_delete_meeting_bot_success(self, db_session: Session):
        """Test deleting a bot"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        bot_id = bot.id

        result = delete_meeting_bot(db_session, bot_id, creator.id)

        assert result is True
        # Verify bot is deleted
        deleted_bot = db_session.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
        assert deleted_bot is None

    def test_delete_meeting_bot_not_found(self, db_session: Session):
        """Test deleting non-existent bot"""
        creator = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        result = delete_meeting_bot(db_session, fake_id, creator.id)

        assert result is False

    def test_delete_meeting_bot_unauthorized(self, db_session: Session):
        """Test non-creator cannot delete bot"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)

        with pytest.raises(Exception):  # HTTPException
            delete_meeting_bot(db_session, bot.id, other_user.id)

    def test_delete_meeting_bot_cascade_logs(self, db_session: Session):
        """Test that deleting bot cascades to logs"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        log_data = MeetingBotLogCreate(action="joined")
        log = create_bot_log(db_session, bot.id, log_data)
        log_id = log.id

        result = delete_meeting_bot(db_session, bot.id, creator.id)

        assert result is True
        # Verify logs are deleted
        logs = db_session.query(MeetingBotLog).filter(MeetingBotLog.meeting_bot_id == bot.id).all()
        assert len(logs) == 0
        # Verify specific log is deleted
        deleted_log = db_session.query(MeetingBotLog).filter(MeetingBotLog.id == log_id).first()
        assert deleted_log is None


class TestCreateBotLog:
    """Tests for create_bot_log function"""

    def test_create_bot_log_success(self, db_session: Session):
        """Test creating a bot log"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        log_data = MeetingBotLogCreate(action="joined", message="Bot joined meeting")

        log = create_bot_log(db_session, bot.id, log_data)

        assert log.id is not None
        assert log.meeting_bot_id == bot.id
        assert log.action == "joined"
        assert log.message == "Bot joined meeting"

    def test_create_bot_log_bot_not_found(self, db_session: Session):
        """Test creating log for non-existent bot"""
        fake_bot_id = uuid.uuid4()
        log_data = MeetingBotLogCreate(action="joined")

        with pytest.raises(Exception):  # HTTPException
            create_bot_log(db_session, fake_bot_id, log_data)

    def test_create_bot_log_minimal_data(self, db_session: Session):
        """Test creating log with minimal data"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        log_data = MeetingBotLogCreate()

        log = create_bot_log(db_session, bot.id, log_data)

        assert log.id is not None
        assert log.meeting_bot_id == bot.id
        assert log.action is None
        assert log.message is None

    def test_create_bot_log_timestamps(self, db_session: Session):
        """Test that log has correct timestamps"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        log_data = MeetingBotLogCreate(action="test")
        before_creation = datetime.now(timezone.utc)

        log = create_bot_log(db_session, bot.id, log_data)

        assert log.created_at is not None
        assert log.created_at >= before_creation


class TestGetBotLogs:
    """Tests for get_bot_logs function"""

    def test_get_bot_logs_success(self, db_session: Session):
        """Test getting logs for a bot"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        log_data1 = MeetingBotLogCreate(action="joined")
        log_data2 = MeetingBotLogCreate(action="recording")
        create_bot_log(db_session, bot.id, log_data1)
        create_bot_log(db_session, bot.id, log_data2)

        logs, total = get_bot_logs(db_session, bot.id)

        assert len(logs) >= 2
        assert total >= 2

    def test_get_bot_logs_pagination(self, db_session: Session):
        """Test getting logs with pagination"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        for i in range(5):
            log_data = MeetingBotLogCreate(action=f"action_{i}")
            create_bot_log(db_session, bot.id, log_data)

        logs, total = get_bot_logs(db_session, bot.id, page=1, limit=2)

        assert len(logs) <= 2
        assert total >= 5

    def test_get_bot_logs_sorted_descending(self, db_session: Session):
        """Test that logs are sorted by created_at descending"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        log1 = create_bot_log(db_session, bot.id, MeetingBotLogCreate(action="first"))
        log2 = create_bot_log(db_session, bot.id, MeetingBotLogCreate(action="second"))

        logs, _ = get_bot_logs(db_session, bot.id)

        # Most recent log should be first
        assert logs[0].created_at >= logs[1].created_at

    def test_get_bot_logs_empty(self, db_session: Session):
        """Test getting logs for bot with no logs"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)

        logs, total = get_bot_logs(db_session, bot.id)

        assert len(logs) == 0
        assert total == 0

    def test_get_bot_logs_invalid_bot(self, db_session: Session):
        """Test getting logs for non-existent bot"""
        fake_bot_id = uuid.uuid4()

        logs, total = get_bot_logs(db_session, fake_bot_id)

        assert len(logs) == 0
        assert total == 0


class TestUpdateBotStatus:
    """Tests for update_bot_status function"""

    def test_update_bot_status_success(self, db_session: Session):
        """Test updating bot status"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator, status="pending")

        updated_bot = update_bot_status(db_session, bot.id, "joined")

        assert updated_bot is not None
        assert updated_bot.status == "joined"

    def test_update_bot_status_not_found(self, db_session: Session):
        """Test updating status for non-existent bot"""
        fake_bot_id = uuid.uuid4()

        result = update_bot_status(db_session, fake_bot_id, "joined")

        assert result is None

    def test_update_bot_status_with_error(self, db_session: Session):
        """Test updating status with error message"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        error_msg = "Connection timeout"

        updated_bot = update_bot_status(db_session, bot.id, "error", error=error_msg)

        assert updated_bot.status == "error"
        assert updated_bot.last_error == error_msg
        assert updated_bot.retry_count == 1

    def test_update_bot_status_with_timestamps(self, db_session: Session):
        """Test updating status with actual timestamps"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        start_time = datetime.now(timezone.utc)
        end_time = datetime.now(timezone.utc) + timedelta(hours=1)

        updated_bot = update_bot_status(
            db_session,
            bot.id,
            "complete",
            actual_start_time=start_time,
            actual_end_time=end_time,
        )

        assert updated_bot.actual_start_time == start_time
        assert updated_bot.actual_end_time == end_time

    def test_update_bot_status_retry_count_increments(self, db_session: Session):
        """Test that retry count increments on error"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)

        # First error
        update_bot_status(db_session, bot.id, "error", error="Error 1")
        db_session.refresh(bot)
        assert bot.retry_count == 1

        # Second error
        update_bot_status(db_session, bot.id, "error", error="Error 2")
        db_session.refresh(bot)
        assert bot.retry_count == 2

    def test_update_bot_status_no_error_no_retry_increment(self, db_session: Session):
        """Test that retry count doesn't increment without error"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)

        update_bot_status(db_session, bot.id, "joined")
        db_session.refresh(bot)

        assert bot.retry_count == 0

    @patch("app.services.meeting_bot.asyncio.create_task")
    def test_update_bot_status_sends_notification(self, mock_create_task, db_session: Session):
        """Test that status update triggers notification"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)

        update_bot_status(db_session, bot.id, "joined")

        # Verify notification task was queued
        assert mock_create_task.called

    def test_update_bot_status_updated_at_timestamp(self, db_session: Session):
        """Test that updated_at is set"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        bot = MeetingBotFactory.create(db_session, meeting, creator)
        original_updated_at = bot.updated_at
        before_update = datetime.now(timezone.utc)

        updated_bot = update_bot_status(db_session, bot.id, "joined")

        assert updated_bot.updated_at is not None
        assert updated_bot.updated_at >= before_update
