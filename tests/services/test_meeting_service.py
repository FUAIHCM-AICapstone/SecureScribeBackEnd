"""Unit tests for meeting service functions"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, ProjectMeeting
from app.schemas.meeting import MeetingCreate, MeetingUpdate
from app.services.meeting import (
    add_meeting_to_project,
    create_meeting,
    delete_meeting,
    get_meeting,
    get_meetings,
    remove_meeting_from_project,
    update_meeting,
)
from tests.factories import MeetingFactory, ProjectFactory, ProjectMeetingFactory, UserFactory, UserProjectFactory


class TestCreateMeeting:
    """Tests for create_meeting function"""

    def test_create_meeting_success(self, db_session: Session):
        """Test creating a meeting with valid data"""
        creator = UserFactory.create(db_session)
        meeting_data = MeetingCreate(
            title="Team Standup",
            description="Daily team standup meeting",
            url="https://zoom.us/j/123456",
            is_personal=False,
        )

        meeting = create_meeting(db_session, meeting_data, creator.id)

        assert meeting.id is not None
        assert meeting.title == "Team Standup"
        assert meeting.description == "Daily team standup meeting"
        assert meeting.url == "https://zoom.us/j/123456"
        assert meeting.created_by == creator.id
        assert meeting.is_personal is False
        assert meeting.status == "active"
        assert meeting.is_deleted is False

    def test_create_personal_meeting(self, db_session: Session):
        """Test creating a personal meeting"""
        creator = UserFactory.create(db_session)
        meeting_data = MeetingCreate(
            title="Personal Notes",
            is_personal=True,
        )

        meeting = create_meeting(db_session, meeting_data, creator.id)

        assert meeting.is_personal is True
        assert meeting.created_by == creator.id

    def test_create_meeting_with_projects(self, db_session: Session):
        """Test creating a meeting linked to projects"""
        creator = UserFactory.create(db_session)
        project1 = ProjectFactory.create(db_session, creator)
        project2 = ProjectFactory.create(db_session, creator)

        meeting_data = MeetingCreate(
            title="Project Meeting",
            is_personal=False,
            project_ids=[project1.id, project2.id],
        )

        meeting = create_meeting(db_session, meeting_data, creator.id)

        # Verify projects are linked
        project_meetings = db_session.query(ProjectMeeting).filter(ProjectMeeting.meeting_id == meeting.id).all()
        assert len(project_meetings) == 2
        project_ids = [pm.project_id for pm in project_meetings]
        assert project1.id in project_ids
        assert project2.id in project_ids

    def test_create_meeting_timestamps(self, db_session: Session):
        """Test that meeting has correct timestamps"""

        creator = UserFactory.create(db_session)
        meeting_data = MeetingCreate(title="Timestamp Test")
        before_creation = datetime.now(timezone.utc)  # Use timezone-aware datetime

        meeting = create_meeting(db_session, meeting_data, creator.id)

        assert meeting.created_at is not None
        assert meeting.created_at >= before_creation

    def test_create_meeting_minimal_data(self, db_session: Session):
        """Test creating a meeting with minimal data"""
        creator = UserFactory.create(db_session)
        meeting_data = MeetingCreate(title="Minimal Meeting")

        meeting = create_meeting(db_session, meeting_data, creator.id)

        assert meeting.title == "Minimal Meeting"
        assert meeting.description is None
        assert meeting.url is None


class TestGetMeeting:
    """Tests for get_meeting function"""

    def test_get_meeting_success(self, db_session: Session):
        """Test getting a meeting by ID"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)

        retrieved_meeting = get_meeting(db_session, meeting.id, creator.id)

        assert retrieved_meeting is not None
        assert retrieved_meeting.id == meeting.id
        assert retrieved_meeting.title == meeting.title

    def test_get_meeting_not_found(self, db_session: Session):
        """Test getting non-existent meeting"""
        creator = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        meeting = get_meeting(db_session, fake_id, creator.id)

        assert meeting is None

    def test_get_meeting_not_found_with_raise(self, db_session: Session):
        """Test getting non-existent meeting with raise_404=True"""
        creator = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        with pytest.raises(Exception):  # HTTPException
            get_meeting(db_session, fake_id, creator.id, raise_404=True)

    def test_get_personal_meeting_owner_access(self, db_session: Session):
        """Test owner can access personal meeting"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, is_personal=True)

        retrieved_meeting = get_meeting(db_session, meeting.id, creator.id)

        assert retrieved_meeting is not None
        assert retrieved_meeting.id == meeting.id

    def test_get_personal_meeting_non_owner_denied(self, db_session: Session):
        """Test non-owner cannot access personal meeting"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, is_personal=True)

        retrieved_meeting = get_meeting(db_session, meeting.id, other_user.id)

        assert retrieved_meeting is None

    def test_get_project_meeting_member_access(self, db_session: Session):
        """Test project member can access project meeting"""
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        UserProjectFactory.create(db_session, member, project, role="member")

        meeting = MeetingFactory.create(db_session, creator, is_personal=False)
        ProjectMeetingFactory.create(db_session, project, meeting)

        retrieved_meeting = get_meeting(db_session, meeting.id, member.id)

        assert retrieved_meeting is not None
        assert retrieved_meeting.id == meeting.id

    def test_get_project_meeting_non_member_denied(self, db_session: Session):
        """Test non-member cannot access project meeting"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)

        meeting = MeetingFactory.create(db_session, creator, is_personal=False)
        ProjectMeetingFactory.create(db_session, project, meeting)

        retrieved_meeting = get_meeting(db_session, meeting.id, other_user.id)

        assert retrieved_meeting is None

    def test_get_deleted_meeting_not_found(self, db_session: Session):
        """Test that deleted meetings are not retrieved"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        meeting.is_deleted = True
        db_session.commit()

        retrieved_meeting = get_meeting(db_session, meeting.id, creator.id)

        assert retrieved_meeting is None


class TestGetMeetings:
    """Tests for get_meetings function"""

    def test_get_meetings_personal_only(self, db_session: Session):
        """Test getting only personal meetings"""
        creator = UserFactory.create(db_session)
        personal_meeting = MeetingFactory.create(db_session, creator, is_personal=True)
        project_meeting = MeetingFactory.create(db_session, creator, is_personal=False)

        meetings, total = get_meetings(db_session, creator.id)

        meeting_ids = [m.id for m in meetings]
        assert personal_meeting.id in meeting_ids
        assert project_meeting.id not in meeting_ids

    def test_get_meetings_with_project_access(self, db_session: Session):
        """Test getting meetings from accessible projects"""
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        UserProjectFactory.create(db_session, member, project, role="member")

        project_meeting = MeetingFactory.create(db_session, creator, is_personal=False)
        ProjectMeetingFactory.create(db_session, project, project_meeting)

        meetings, total = get_meetings(db_session, member.id)

        meeting_ids = [m.id for m in meetings]
        assert project_meeting.id in meeting_ids

    def test_get_meetings_pagination(self, db_session: Session):
        """Test getting meetings with pagination"""
        creator = UserFactory.create(db_session)
        for _ in range(5):
            MeetingFactory.create(db_session, creator, is_personal=True)

        meetings, total = get_meetings(db_session, creator.id, page=1, limit=2)

        assert len(meetings) <= 2
        assert total >= 5

    def test_get_meetings_filter_by_title(self, db_session: Session):
        """Test filtering meetings by title"""
        creator = UserFactory.create(db_session)
        MeetingFactory.create(db_session, creator, title="Standup Meeting", is_personal=True)
        MeetingFactory.create(db_session, creator, title="Planning Session", is_personal=True)

        from app.schemas.meeting import MeetingFilter

        filters = MeetingFilter(title="Standup")
        meetings, total = get_meetings(db_session, creator.id, filters=filters)

        assert len(meetings) >= 1
        assert any("Standup" in m.title for m in meetings)

    def test_get_meetings_filter_by_status(self, db_session: Session):
        """Test filtering meetings by status"""
        creator = UserFactory.create(db_session)
        meeting1 = MeetingFactory.create(db_session, creator, status="active", is_personal=True)
        meeting2 = MeetingFactory.create(db_session, creator, status="completed", is_personal=True)

        from app.schemas.meeting import MeetingFilter

        filters = MeetingFilter(status="active")
        meetings, total = get_meetings(db_session, creator.id, filters=filters)

        meeting_ids = [m.id for m in meetings]
        assert meeting1.id in meeting_ids
        assert meeting2.id not in meeting_ids

    def test_get_meetings_excludes_deleted(self, db_session: Session):
        """Test that deleted meetings are excluded"""
        creator = UserFactory.create(db_session)
        active_meeting = MeetingFactory.create(db_session, creator, is_personal=True)
        deleted_meeting = MeetingFactory.create(db_session, creator, is_personal=True)
        deleted_meeting.is_deleted = True
        db_session.commit()

        meetings, total = get_meetings(db_session, creator.id)

        meeting_ids = [m.id for m in meetings]
        assert active_meeting.id in meeting_ids
        assert deleted_meeting.id not in meeting_ids

    def test_get_meetings_default_pagination(self, db_session: Session):
        """Test default pagination values"""
        creator = UserFactory.create(db_session)
        for _ in range(25):
            MeetingFactory.create(db_session, creator, is_personal=True)

        meetings, total = get_meetings(db_session, creator.id)

        assert len(meetings) <= 20  # Default limit


class TestUpdateMeeting:
    """Tests for update_meeting function"""

    def test_update_meeting_success(self, db_session: Session):
        """Test updating a meeting with valid data"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, title="Original Title")
        updates = MeetingUpdate(title="Updated Title", description="Updated description")

        updated_meeting = update_meeting(db_session, meeting.id, updates, creator.id)

        assert updated_meeting is not None
        assert updated_meeting.title == "Updated Title"
        assert updated_meeting.description == "Updated description"
        assert updated_meeting.id == meeting.id

    def test_update_meeting_not_found(self, db_session: Session):
        """Test updating non-existent meeting"""
        creator = UserFactory.create(db_session)
        fake_id = uuid.uuid4()
        updates = MeetingUpdate(title="Updated Title")

        result = update_meeting(db_session, fake_id, updates, creator.id)

        assert result is None

    def test_update_meeting_partial_fields(self, db_session: Session):
        """Test updating only some fields"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(
            db_session,
            creator,
            title="Original",
            description="Original description",
        )
        updates = MeetingUpdate(title="Updated")

        updated_meeting = update_meeting(db_session, meeting.id, updates, creator.id)

        assert updated_meeting.title == "Updated"
        assert updated_meeting.description == "Original description"

    def test_update_meeting_status(self, db_session: Session):
        """Test updating meeting status"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, status="active")
        updates = MeetingUpdate(status="completed")

        updated_meeting = update_meeting(db_session, meeting.id, updates, creator.id)

        assert updated_meeting.status == "completed"

    def test_update_meeting_url(self, db_session: Session):
        """Test updating meeting URL"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, url="https://zoom.us/j/123")
        updates = MeetingUpdate(url="https://zoom.us/j/456")

        updated_meeting = update_meeting(db_session, meeting.id, updates, creator.id)

        assert updated_meeting.url == "https://zoom.us/j/456"

    def test_update_meeting_invalid_url(self, db_session: Session):
        """Test updating meeting with invalid URL"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        updates = MeetingUpdate(url="not-a-valid-url")

        result = update_meeting(db_session, meeting.id, updates, creator.id)

        assert result is None

    def test_update_meeting_empty_updates(self, db_session: Session):
        """Test updating meeting with no changes"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, title="Original")
        updates = MeetingUpdate()

        updated_meeting = update_meeting(db_session, meeting.id, updates, creator.id)

        assert updated_meeting.title == "Original"
        assert updated_meeting.id == meeting.id


class TestDeleteMeeting:
    """Tests for delete_meeting function"""

    def test_delete_meeting_success(self, db_session: Session):
        """Test deleting a meeting"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        meeting_id = meeting.id

        result = delete_meeting(db_session, meeting_id, creator.id)

        assert result is True
        # Verify meeting is soft deleted
        deleted_meeting = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
        assert deleted_meeting is not None
        assert deleted_meeting.is_deleted is True

    def test_delete_meeting_not_found(self, db_session: Session):
        """Test deleting non-existent meeting"""
        creator = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        result = delete_meeting(db_session, fake_id, creator.id)

        assert result is False

    def test_delete_meeting_non_owner_denied(self, db_session: Session):
        """Test non-owner cannot delete meeting"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator, is_personal=True)

        result = delete_meeting(db_session, meeting.id, other_user.id)

        assert result is False

    def test_delete_meeting_project_admin_allowed(self, db_session: Session):
        """Test project admin can delete project meeting"""
        creator = UserFactory.create(db_session)
        admin = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        UserProjectFactory.create(db_session, admin, project, role="admin")

        meeting = MeetingFactory.create(db_session, creator, is_personal=False)
        ProjectMeetingFactory.create(db_session, project, meeting)

        result = delete_meeting(db_session, meeting.id, admin.id)

        assert result is True

    def test_delete_meeting_cascade_cleanup_files(self, db_session: Session):
        """Test that deleting meeting cleans up associated files"""
        from tests.factories import FileFactory

        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        file = FileFactory.create(db_session, creator, meeting=meeting)

        result = delete_meeting(db_session, meeting.id, creator.id)

        assert result is True
        # Verify file is deleted
        from app.models.file import File

        deleted_file = db_session.query(File).filter(File.id == file.id).first()
        assert deleted_file is None

    def test_delete_meeting_already_deleted(self, db_session: Session):
        """Test deleting already deleted meeting"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        meeting.is_deleted = True
        db_session.commit()

        result = delete_meeting(db_session, meeting.id, creator.id)

        assert result is False


class TestAddMeetingToProject:
    """Tests for add_meeting_to_project function"""

    def test_add_meeting_to_project_success(self, db_session: Session):
        """Test adding a meeting to a project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        meeting = MeetingFactory.create(db_session, creator, is_personal=True)

        result = add_meeting_to_project(db_session, meeting.id, project.id, creator.id)

        assert result is True
        # Verify relationship is created
        project_meeting = (
            db_session.query(ProjectMeeting)
            .filter(
                ProjectMeeting.meeting_id == meeting.id,
                ProjectMeeting.project_id == project.id,
            )
            .first()
        )
        assert project_meeting is not None

    def test_add_meeting_to_project_already_linked(self, db_session: Session):
        """Test adding meeting already linked to project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        meeting = MeetingFactory.create(db_session, creator, is_personal=False)
        ProjectMeetingFactory.create(db_session, project, meeting)

        result = add_meeting_to_project(db_session, meeting.id, project.id, creator.id)

        assert result is True

    def test_add_meeting_to_project_not_found_meeting(self, db_session: Session):
        """Test adding non-existent meeting to project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        fake_meeting_id = uuid.uuid4()

        result = add_meeting_to_project(db_session, fake_meeting_id, project.id, creator.id)

        assert result is False

    def test_add_meeting_to_project_not_found_project(self, db_session: Session):
        """Test adding meeting to non-existent project"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        fake_project_id = uuid.uuid4()

        result = add_meeting_to_project(db_session, meeting.id, fake_project_id, creator.id)

        assert result is False

    def test_add_meeting_to_project_changes_personal_flag(self, db_session: Session):
        """Test that adding to project changes is_personal flag"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        meeting = MeetingFactory.create(db_session, creator, is_personal=True)

        add_meeting_to_project(db_session, meeting.id, project.id, creator.id)

        # Refresh to get updated data
        db_session.refresh(meeting)
        assert meeting.is_personal is False


class TestRemoveMeetingFromProject:
    """Tests for remove_meeting_from_project function"""

    def test_remove_meeting_from_project_success(self, db_session: Session):
        """Test removing a meeting from a project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        meeting = MeetingFactory.create(db_session, creator, is_personal=False)
        ProjectMeetingFactory.create(db_session, project, meeting)

        result = remove_meeting_from_project(db_session, meeting.id, project.id, creator.id)

        assert result is True
        # Verify relationship is deleted
        project_meeting = (
            db_session.query(ProjectMeeting)
            .filter(
                ProjectMeeting.meeting_id == meeting.id,
                ProjectMeeting.project_id == project.id,
            )
            .first()
        )
        assert project_meeting is None

    def test_remove_meeting_from_project_not_linked(self, db_session: Session):
        """Test removing meeting not linked to project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        meeting = MeetingFactory.create(db_session, creator)

        result = remove_meeting_from_project(db_session, meeting.id, project.id, creator.id)

        assert result is False

    def test_remove_meeting_from_project_not_found_meeting(self, db_session: Session):
        """Test removing non-existent meeting from project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        fake_meeting_id = uuid.uuid4()

        result = remove_meeting_from_project(db_session, fake_meeting_id, project.id, creator.id)

        assert result is False

    def test_remove_meeting_from_project_not_found_project(self, db_session: Session):
        """Test removing meeting from non-existent project"""
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, creator)
        fake_project_id = uuid.uuid4()

        result = remove_meeting_from_project(db_session, meeting.id, fake_project_id, creator.id)

        assert result is False
