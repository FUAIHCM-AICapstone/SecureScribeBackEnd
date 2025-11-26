"""API endpoint tests for meeting endpoints"""

import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, ProjectMeeting
from tests.factories import (
    MeetingBotFactory,
    MeetingFactory,
    ProjectFactory,
    ProjectMeetingFactory,
    UserFactory,
    UserProjectFactory,
)

fake = Faker()


class TestCreateMeetingEndpoint:
    """Tests for POST /meetings endpoint"""

    def test_create_meeting_success(self, client: TestClient, db_session: Session):
        """Test creating a meeting via API"""
        meeting_title = fake.sentence(nb_words=3)
        meeting_description = fake.text(max_nb_chars=100)
        meeting_url = fake.url()
        
        meeting_data = {
            "title": meeting_title,
            "description": meeting_description,
            "url": meeting_url,
            "is_personal": False,
        }

        response = client.post("/api/v1/meetings", json=meeting_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == meeting_title
        assert data["data"]["url"] == meeting_url
        assert data["data"]["is_personal"] is False

        # Verify data persisted to database
        meeting = db_session.query(Meeting).filter(Meeting.title == meeting_title).first()
        assert meeting is not None

    def test_create_personal_meeting(self, client: TestClient, db_session: Session):
        """Test creating a personal meeting"""
        meeting_data = {
            "title": "Personal Notes",
            "is_personal": True,
        }

        response = client.post("/api/v1/meetings", json=meeting_data)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_personal"] is True

        # Verify in database
        meeting = db_session.query(Meeting).filter(Meeting.title == "Personal Notes").first()
        assert meeting is not None
        assert meeting.is_personal is True

    def test_create_meeting_with_projects(self, client: TestClient, db_session: Session, test_user):
        """Test creating a meeting linked to projects"""
        project1 = ProjectFactory.create(db_session, test_user)
        project2 = ProjectFactory.create(db_session, test_user)

        meeting_data = {
            "title": "Project Meeting",
            "is_personal": False,
            "project_ids": [str(project1.id), str(project2.id)],
        }

        response = client.post("/api/v1/meetings", json=meeting_data)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "Project Meeting"

        # Verify projects are linked in database
        meeting = db_session.query(Meeting).filter(Meeting.title == "Project Meeting").first()
        project_meetings = db_session.query(ProjectMeeting).filter(ProjectMeeting.meeting_id == meeting.id).all()
        assert len(project_meetings) == 2

    def test_create_meeting_minimal_data(self, client: TestClient, db_session: Session):
        """Test creating a meeting with minimal data"""
        meeting_data = {"title": "Minimal Meeting"}

        response = client.post("/api/v1/meetings", json=meeting_data)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "Minimal Meeting"

    def test_create_meeting_with_empty_title(self, client: TestClient):
        """Test creating a meeting with empty title"""
        meeting_data = {"title": ""}

        response = client.post("/api/v1/meetings", json=meeting_data)

        # Empty title is allowed, just verify it's created
        assert response.status_code == 200

    def test_create_meeting_unauthenticated(self, unauthenticated_client: TestClient):
        """Test creating a meeting without authentication fails"""
        meeting_data = {"title": "Test Meeting"}

        response = unauthenticated_client.post("/api/v1/meetings", json=meeting_data)

        assert response.status_code == 403  # Forbidden


class TestGetMeetingsEndpoint:
    """Tests for GET /meetings endpoint"""

    def test_get_meetings_success(self, client: TestClient, db_session: Session, test_user):
        """Test getting meetings list"""
        MeetingFactory.create(db_session, test_user, is_personal=True)
        MeetingFactory.create(db_session, test_user, is_personal=True)

        response = client.get("/api/v1/meetings")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 2
        assert "pagination" in data

    def test_get_meetings_pagination(self, client: TestClient, db_session: Session, test_user):
        """Test getting meetings with pagination"""
        for _ in range(5):
            MeetingFactory.create(db_session, test_user, is_personal=True)

        response = client.get("/api/v1/meetings?page=1&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 2
        assert data["pagination"]["total"] >= 5
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 2

    def test_get_meetings_filter_by_title(self, client: TestClient, db_session: Session, test_user):
        """Test filtering meetings by title"""
        MeetingFactory.create(db_session, test_user, title="Standup Meeting", is_personal=True)
        MeetingFactory.create(db_session, test_user, title="Planning Session", is_personal=True)

        response = client.get("/api/v1/meetings?title=Standup")

        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert any("Standup" in m["title"] for m in data["data"])

    def test_get_meetings_filter_by_status(self, client: TestClient, db_session: Session, test_user):
        """Test filtering meetings by status"""
        MeetingFactory.create(db_session, test_user, status="active", is_personal=True)
        MeetingFactory.create(db_session, test_user, status="completed", is_personal=True)

        response = client.get("/api/v1/meetings?status=active")

        assert response.status_code == 200
        data = response.json()
        assert all(m["status"] == "active" for m in data["data"])

    def test_get_meetings_filter_by_is_personal(self, client: TestClient, db_session: Session, test_user):
        """Test filtering meetings by is_personal"""
        MeetingFactory.create(db_session, test_user, is_personal=True)
        project = ProjectFactory.create(db_session, test_user)
        meeting = MeetingFactory.create(db_session, test_user, is_personal=False)
        ProjectMeetingFactory.create(db_session, project, meeting)

        response = client.get("/api/v1/meetings?is_personal=true")

        assert response.status_code == 200
        data = response.json()
        assert all(m["is_personal"] is True for m in data["data"])

    def test_get_meetings_only_accessible(self, client: TestClient, db_session: Session, test_user):
        """Test that only accessible meetings are returned"""
        other_user = UserFactory.create(db_session)
        personal_meeting = MeetingFactory.create(db_session, test_user, is_personal=True)
        other_personal = MeetingFactory.create(db_session, other_user, is_personal=True)

        response = client.get("/api/v1/meetings")

        assert response.status_code == 200
        data = response.json()
        meeting_ids = [m["id"] for m in data["data"]]
        assert str(personal_meeting.id) in meeting_ids
        assert str(other_personal.id) not in meeting_ids

    def test_get_meetings_project_member_access(self, client: TestClient, db_session: Session, test_user):
        """Test project members can access project meetings"""
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, test_user)
        UserProjectFactory.create(db_session, member, project, role="member")

        meeting = MeetingFactory.create(db_session, test_user, is_personal=False)
        ProjectMeetingFactory.create(db_session, project, meeting)

        # Create client for member
        from app.utils.auth import create_access_token

        token = create_access_token({"sub": str(member.id)})
        member_client = TestClient(client.app)
        member_client.headers.update({"Authorization": f"Bearer {token}"})

        response = member_client.get("/api/v1/meetings")

        assert response.status_code == 200
        data = response.json()
        meeting_ids = [m["id"] for m in data["data"]]
        assert str(meeting.id) in meeting_ids

    def test_get_meetings_unauthenticated(self, unauthenticated_client: TestClient):
        """Test getting meetings without authentication fails"""
        response = unauthenticated_client.get("/api/v1/meetings")

        assert response.status_code == 403


class TestGetMeetingEndpoint:
    """Tests for GET /meetings/{meeting_id} endpoint"""

    def test_get_meeting_success(self, client: TestClient, db_session: Session, test_user):
        """Test getting a specific meeting"""
        meeting = MeetingFactory.create(db_session, test_user, is_personal=True)

        response = client.get(f"/api/v1/meetings/{meeting.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == str(meeting.id)
        assert data["data"]["title"] == meeting.title

    def test_get_meeting_with_projects(self, client: TestClient, db_session: Session, test_user):
        """Test getting meeting includes project information"""
        project = ProjectFactory.create(db_session, test_user)
        meeting = MeetingFactory.create(db_session, test_user, is_personal=False)
        ProjectMeetingFactory.create(db_session, project, meeting)

        response = client.get(f"/api/v1/meetings/{meeting.id}")

        assert response.status_code == 200
        data = response.json()
        assert "projects" in data["data"]
        assert len(data["data"]["projects"]) >= 1

    def test_get_meeting_not_found(self, client: TestClient):
        """Test getting non-existent meeting"""
        fake_id = uuid.uuid4()

        response = client.get(f"/api/v1/meetings/{fake_id}")

        assert response.status_code == 404

    def test_get_meeting_access_denied(self, client: TestClient, db_session: Session):
        """Test accessing meeting without permission"""
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, other_user, is_personal=True)

        response = client.get(f"/api/v1/meetings/{meeting.id}")

        assert response.status_code == 404

    def test_get_meeting_unauthenticated(self, unauthenticated_client: TestClient, db_session: Session, test_user):
        """Test getting meeting without authentication fails"""
        meeting = MeetingFactory.create(db_session, test_user)

        response = unauthenticated_client.get(f"/api/v1/meetings/{meeting.id}")

        assert response.status_code == 403


class TestUpdateMeetingEndpoint:
    """Tests for PUT /meetings/{meeting_id} endpoint"""

    def test_update_meeting_success(self, client: TestClient, db_session: Session, test_user):
        """Test updating a meeting"""
        meeting = MeetingFactory.create(db_session, test_user, title="Original Title")
        updates = {
            "title": "Updated Title",
            "description": "Updated description",
        }

        response = client.put(f"/api/v1/meetings/{meeting.id}", json=updates)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "Updated Title"
        assert data["data"]["description"] == "Updated description"

        # Verify changes persisted to database
        db_session.refresh(meeting)
        assert meeting.title == "Updated Title"
        assert meeting.description == "Updated description"

    def test_update_meeting_partial_fields(self, client: TestClient, db_session: Session, test_user):
        """Test updating only some fields"""
        meeting = MeetingFactory.create(
            db_session,
            test_user,
            title="Original",
            description="Original description",
        )
        updates = {"title": "Updated"}

        response = client.put(f"/api/v1/meetings/{meeting.id}", json=updates)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "Updated"
        assert data["data"]["description"] == "Original description"

    def test_update_meeting_status(self, client: TestClient, db_session: Session, test_user):
        """Test updating meeting status"""
        meeting = MeetingFactory.create(db_session, test_user, status="active")
        updates = {"status": "completed"}

        response = client.put(f"/api/v1/meetings/{meeting.id}", json=updates)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "completed"

        # Verify in database
        db_session.refresh(meeting)
        assert meeting.status == "completed"

    def test_update_meeting_url(self, client: TestClient, db_session: Session, test_user):
        """Test updating meeting URL"""
        meeting = MeetingFactory.create(db_session, test_user, url="https://zoom.us/j/123")
        updates = {"url": "https://zoom.us/j/456"}

        response = client.put(f"/api/v1/meetings/{meeting.id}", json=updates)

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["url"] == "https://zoom.us/j/456"

    def test_update_meeting_not_found(self, client: TestClient):
        """Test updating non-existent meeting"""
        fake_id = uuid.uuid4()
        updates = {"title": "Updated"}

        response = client.put(f"/api/v1/meetings/{fake_id}", json=updates)

        assert response.status_code == 404

    def test_update_meeting_access_denied(self, client: TestClient, db_session: Session):
        """Test updating meeting without permission"""
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, other_user, is_personal=True)
        updates = {"title": "Updated"}

        response = client.put(f"/api/v1/meetings/{meeting.id}", json=updates)

        assert response.status_code == 404

    def test_update_meeting_unauthenticated(self, unauthenticated_client: TestClient, db_session: Session, test_user):
        """Test updating meeting without authentication fails"""
        meeting = MeetingFactory.create(db_session, test_user)
        updates = {"title": "Updated"}

        response = unauthenticated_client.put(f"/api/v1/meetings/{meeting.id}", json=updates)

        assert response.status_code == 403


class TestDeleteMeetingEndpoint:
    """Tests for DELETE /meetings/{meeting_id} endpoint"""

    def test_delete_meeting_success(self, client: TestClient, db_session: Session, test_user):
        """Test deleting a meeting"""
        meeting = MeetingFactory.create(db_session, test_user)
        meeting_id = meeting.id

        response = client.delete(f"/api/v1/meetings/{meeting_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify soft deleted in database - refresh to get latest state
        db_session.expire_all()
        deleted_meeting = db_session.query(Meeting).filter(Meeting.id == meeting_id).first()
        assert deleted_meeting is not None
        # Meeting should be soft deleted
        assert deleted_meeting.is_deleted is True

    def test_delete_meeting_not_found(self, client: TestClient):
        """Test deleting non-existent meeting"""
        fake_id = uuid.uuid4()

        response = client.delete(f"/api/v1/meetings/{fake_id}")

        assert response.status_code == 404

    def test_delete_meeting_access_denied(self, client: TestClient, db_session: Session):
        """Test deleting meeting without permission returns 404"""
        other_user = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, other_user, is_personal=True)

        response = client.delete(f"/api/v1/meetings/{meeting.id}")

        # Access denied returns 404 (not found) to avoid leaking information
        assert response.status_code == 404

    def test_delete_meeting_project_admin_allowed(self, client: TestClient, db_session: Session, test_user):
        """Test project admin can delete project meeting"""
        admin = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, test_user)
        UserProjectFactory.create(db_session, admin, project, role="admin")

        meeting = MeetingFactory.create(db_session, test_user, is_personal=False)
        ProjectMeetingFactory.create(db_session, project, meeting)

        # Create client for admin
        from app.utils.auth import create_access_token

        token = create_access_token({"sub": str(admin.id)})
        admin_client = TestClient(client.app)
        admin_client.headers.update({"Authorization": f"Bearer {token}"})

        response = admin_client.delete(f"/api/v1/meetings/{meeting.id}")

        assert response.status_code == 200

    def test_delete_meeting_unauthenticated(self, unauthenticated_client: TestClient, db_session: Session, test_user):
        """Test deleting meeting without authentication fails"""
        meeting = MeetingFactory.create(db_session, test_user)

        response = unauthenticated_client.delete(f"/api/v1/meetings/{meeting.id}")

        assert response.status_code == 403


class TestAddMeetingToProjectEndpoint:
    """Tests for POST /projects/{project_id}/meetings/{meeting_id} endpoint"""

    def test_add_meeting_to_project_success(self, client: TestClient, db_session: Session, test_user):
        """Test adding a meeting to a project"""
        project = ProjectFactory.create(db_session, test_user)
        meeting = MeetingFactory.create(db_session, test_user, is_personal=True)

        response = client.post(f"/api/v1/projects/{project.id}/meetings/{meeting.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify relationship created in database
        project_meeting = (
            db_session.query(ProjectMeeting)
            .filter(
                ProjectMeeting.meeting_id == meeting.id,
                ProjectMeeting.project_id == project.id,
            )
            .first()
        )
        assert project_meeting is not None

    def test_add_meeting_to_project_already_linked(self, client: TestClient, db_session: Session, test_user):
        """Test adding meeting already linked to project"""
        project = ProjectFactory.create(db_session, test_user)
        meeting = MeetingFactory.create(db_session, test_user, is_personal=False)
        ProjectMeetingFactory.create(db_session, project, meeting)

        response = client.post(f"/api/v1/projects/{project.id}/meetings/{meeting.id}")

        assert response.status_code == 200

    def test_add_meeting_to_project_not_found_meeting(self, client: TestClient, db_session: Session, test_user):
        """Test adding non-existent meeting to project"""
        project = ProjectFactory.create(db_session, test_user)
        fake_meeting_id = uuid.uuid4()

        response = client.post(f"/api/v1/projects/{project.id}/meetings/{fake_meeting_id}")

        assert response.status_code == 400

    def test_add_meeting_to_project_not_found_project(self, client: TestClient, db_session: Session, test_user):
        """Test adding meeting to non-existent project"""
        meeting = MeetingFactory.create(db_session, test_user)
        fake_project_id = uuid.uuid4()

        response = client.post(f"/api/v1/projects/{fake_project_id}/meetings/{meeting.id}")

        assert response.status_code == 400

    def test_add_meeting_to_project_unauthenticated(self, unauthenticated_client: TestClient, db_session: Session, test_user):
        """Test adding meeting to project without authentication fails"""
        project = ProjectFactory.create(db_session, test_user)
        meeting = MeetingFactory.create(db_session, test_user)

        response = unauthenticated_client.post(f"/api/v1/projects/{project.id}/meetings/{meeting.id}")

        assert response.status_code == 403


class TestRemoveMeetingFromProjectEndpoint:
    """Tests for DELETE /projects/{project_id}/meetings/{meeting_id} endpoint"""

    def test_remove_meeting_from_project_success(self, client: TestClient, db_session: Session, test_user):
        """Test removing a meeting from a project"""
        project = ProjectFactory.create(db_session, test_user)
        meeting = MeetingFactory.create(db_session, test_user, is_personal=False)
        ProjectMeetingFactory.create(db_session, project, meeting)

        response = client.delete(f"/api/v1/projects/{project.id}/meetings/{meeting.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify relationship deleted from database
        project_meeting = (
            db_session.query(ProjectMeeting)
            .filter(
                ProjectMeeting.meeting_id == meeting.id,
                ProjectMeeting.project_id == project.id,
            )
            .first()
        )
        assert project_meeting is None

    def test_remove_meeting_from_project_not_linked(self, client: TestClient, db_session: Session, test_user):
        """Test removing meeting not linked to project"""
        project = ProjectFactory.create(db_session, test_user)
        meeting = MeetingFactory.create(db_session, test_user)

        response = client.delete(f"/api/v1/projects/{project.id}/meetings/{meeting.id}")

        assert response.status_code == 400

    def test_remove_meeting_from_project_not_found_meeting(self, client: TestClient, db_session: Session, test_user):
        """Test removing non-existent meeting from project"""
        project = ProjectFactory.create(db_session, test_user)
        fake_meeting_id = uuid.uuid4()

        response = client.delete(f"/api/v1/projects/{project.id}/meetings/{fake_meeting_id}")

        assert response.status_code == 400

    def test_remove_meeting_from_project_not_found_project(self, client: TestClient, db_session: Session, test_user):
        """Test removing meeting from non-existent project"""
        meeting = MeetingFactory.create(db_session, test_user)
        fake_project_id = uuid.uuid4()

        response = client.delete(f"/api/v1/projects/{fake_project_id}/meetings/{meeting.id}")

        assert response.status_code == 400

    def test_remove_meeting_from_project_unauthenticated(self, unauthenticated_client: TestClient, db_session: Session, test_user):
        """Test removing meeting from project without authentication fails"""
        project = ProjectFactory.create(db_session, test_user)
        meeting = MeetingFactory.create(db_session, test_user)

        response = unauthenticated_client.delete(f"/api/v1/projects/{project.id}/meetings/{meeting.id}")

        assert response.status_code == 403


class TestMeetingBotManagementEndpoints:
    """Tests for meeting bot management endpoints (join, leave, status)"""

    def test_bot_join_meeting_creates_bot(self, client: TestClient, db_session: Session, test_user):
        """Test that bot join creates a meeting bot record"""
        meeting = MeetingFactory.create(db_session, test_user)

        # Create bot via service (simulating bot join)
        from app.schemas.meeting_bot import MeetingBotCreate
        from app.services.meeting_bot import create_meeting_bot

        bot_data = MeetingBotCreate(
            meeting_id=meeting.id,
            meeting_url="https://zoom.us/j/123456",
        )
        bot = create_meeting_bot(db_session, bot_data, test_user.id)

        assert bot.id is not None
        assert bot.meeting_id == meeting.id
        assert bot.status == "pending"

        # Verify in database
        from app.models.meeting import MeetingBot

        db_bot = db_session.query(MeetingBot).filter(MeetingBot.id == bot.id).first()
        assert db_bot is not None
        assert db_bot.meeting_id == meeting.id

    def test_bot_status_update_persists(self, client: TestClient, db_session: Session, test_user):
        """Test that bot status updates persist to database"""
        meeting = MeetingFactory.create(db_session, test_user)
        bot = MeetingBotFactory.create(db_session, meeting, test_user, status="pending")

        # Update status
        from app.services.meeting_bot import update_bot_status

        updated_bot = update_bot_status(db_session, bot.id, "joined")

        assert updated_bot.status == "joined"

        # Verify in database
        db_session.refresh(bot)
        assert bot.status == "joined"

    def test_bot_recording_status_transition(self, client: TestClient, db_session: Session, test_user):
        """Test bot status transitions through recording lifecycle"""
        meeting = MeetingFactory.create(db_session, test_user)
        bot = MeetingBotFactory.create(db_session, meeting, test_user, status="pending")

        from app.services.meeting_bot import update_bot_status

        # Transition through states
        update_bot_status(db_session, bot.id, "joined")
        db_session.refresh(bot)
        assert bot.status == "joined"

        update_bot_status(db_session, bot.id, "recording")
        db_session.refresh(bot)
        assert bot.status == "recording"

        update_bot_status(db_session, bot.id, "complete")
        db_session.refresh(bot)
        assert bot.status == "complete"

    def test_bot_error_status_with_retry_count(self, client: TestClient, db_session: Session, test_user):
        """Test bot error status increments retry count"""
        meeting = MeetingFactory.create(db_session, test_user)
        bot = MeetingBotFactory.create(db_session, meeting, test_user)

        from app.services.meeting_bot import update_bot_status

        # First error
        update_bot_status(db_session, bot.id, "error", error="Connection failed")
        db_session.refresh(bot)
        assert bot.status == "error"
        assert bot.retry_count == 1
        assert bot.last_error == "Connection failed"

        # Second error
        update_bot_status(db_session, bot.id, "error", error="Timeout")
        db_session.refresh(bot)
        assert bot.retry_count == 2
        assert bot.last_error == "Timeout"

    def test_bot_timestamps_on_status_change(self, client: TestClient, db_session: Session, test_user):
        """Test bot actual_start_time and actual_end_time are set correctly"""
        meeting = MeetingFactory.create(db_session, test_user)
        bot = MeetingBotFactory.create(db_session, meeting, test_user)

        from app.services.meeting_bot import update_bot_status

        start_time = datetime.now(timezone.utc)
        update_bot_status(db_session, bot.id, "recording", actual_start_time=start_time)
        db_session.refresh(bot)
        assert bot.actual_start_time == start_time

        end_time = datetime.now(timezone.utc) + timedelta(hours=1)
        update_bot_status(db_session, bot.id, "complete", actual_end_time=end_time)
        db_session.refresh(bot)
        assert bot.actual_end_time == end_time

    def test_bot_deletion_cascades_logs(self, client: TestClient, db_session: Session, test_user):
        """Test that deleting bot cascades to logs"""
        meeting = MeetingFactory.create(db_session, test_user)
        bot = MeetingBotFactory.create(db_session, meeting, test_user)

        from app.schemas.meeting_bot import MeetingBotLogCreate
        from app.services.meeting_bot import create_bot_log, delete_meeting_bot

        # Create logs
        create_bot_log(db_session, bot.id, MeetingBotLogCreate(action="joined"))
        create_bot_log(db_session, bot.id, MeetingBotLogCreate(action="recording"))

        # Delete bot
        result = delete_meeting_bot(db_session, bot.id, test_user.id)
        assert result is True

        # Verify logs are deleted
        from app.models.meeting import MeetingBotLog

        logs = db_session.query(MeetingBotLog).filter(MeetingBotLog.meeting_bot_id == bot.id).all()
        assert len(logs) == 0
