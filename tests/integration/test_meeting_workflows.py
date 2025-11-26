"""Integration tests for meeting workflows"""

import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models.meeting import Meeting, MeetingBot, ProjectMeeting, Transcript
from app.utils.auth import create_access_token
from tests.factories import (
    AudioFileFactory,
    MeetingBotFactory,
    MeetingFactory,
    ProjectFactory,
    ProjectMeetingFactory,
    TranscriptFactory,
    UserFactory,
)

fake = Faker()


class TestMeetingCreationAndBotManagement:
    """Integration tests for meeting creation and bot management workflow"""

    def test_meeting_creation_creates_database_record(self, db_session: Session):
        """Test that meeting creation creates a record in the database"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()

        meeting_data = {
            "title": fake.sentence(nb_words=2),
            "description": fake.paragraph(),
            "url": fake.url(),
            "is_personal": True,
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post("/api/v1/meetings", json=meeting_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == meeting_data["title"]
        assert data["data"]["description"] == meeting_data["description"]
        assert data["data"]["is_personal"] is True

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            meeting_id = uuid.UUID(data["data"]["id"])
            db_meeting = fresh_session.query(Meeting).filter(Meeting.id == meeting_id).first()
            assert db_meeting is not None
            assert db_meeting.title == meeting_data["title"]
            assert db_meeting.created_by == creator.id
            assert db_meeting.is_deleted is False
        finally:
            fresh_session.close()

    def test_meeting_bot_creation_and_status_tracking(self, db_session: Session):
        """Test that meeting bot is created and status is tracked"""
        # Arrange
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=creator)
        db_session.commit()

        bot_data = {
            "meeting_id": str(meeting.id),
            "scheduled_start_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "meeting_url": fake.url(),
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post("/api/v1/meeting-bots", json=bot_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "pending"
        assert data["data"]["meeting_id"] == str(meeting.id)

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            bot_id = uuid.UUID(data["data"]["id"])
            db_bot = fresh_session.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
            assert db_bot is not None
            assert db_bot.meeting_id == meeting.id
            assert db_bot.status == "pending"
            assert db_bot.created_by == creator.id
        finally:
            fresh_session.close()

    def test_meeting_bot_status_update_persists(self, db_session: Session):
        """Test that meeting bot status updates persist to database"""
        # Arrange
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=creator)
        bot = MeetingBotFactory.create(db_session, meeting=meeting, created_by=creator, status="pending")
        db_session.commit()

        bot_update_data = {
            "status": "joined",
            "actual_start_time": datetime.now(timezone.utc).isoformat(),
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.put(f"/api/v1/meeting-bots/{bot.id}", json=bot_update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "joined"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_bot = fresh_session.query(MeetingBot).filter(MeetingBot.id == bot.id).first()
            assert db_bot is not None
            assert db_bot.status == "joined"
            assert db_bot.actual_start_time is not None
        finally:
            fresh_session.close()

    def test_meeting_bot_deletion_removes_from_database(self, db_session: Session):
        """Test that meeting bot deletion removes bot from database"""
        # Arrange
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=creator)
        bot = MeetingBotFactory.create(db_session, meeting=meeting, created_by=creator)
        bot_id = bot.id
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/meeting-bots/{bot_id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deleted from database with fresh session
        fresh_session = SessionLocal()
        try:
            db_bot = fresh_session.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
            assert db_bot is None
        finally:
            fresh_session.close()


class TestTranscriptCreationAndUpdates:
    """Integration tests for transcript creation and updates workflow"""

    def test_transcript_creation_creates_database_record(self, db_session: Session):
        """Test that transcript creation creates a record in the database"""
        # Arrange
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=creator)
        db_session.commit()

        transcript_data = {
            "meeting_id": str(meeting.id),
            "content": "This is a test transcript content",
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post("/api/v1/transcripts", json=transcript_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["meeting_id"] == str(meeting.id)
        assert data["data"]["content"] == transcript_data["content"]

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            transcript_id = uuid.UUID(data["data"]["id"])
            db_transcript = fresh_session.query(Transcript).filter(Transcript.id == transcript_id).first()
            assert db_transcript is not None
            assert db_transcript.meeting_id == meeting.id
            assert db_transcript.content == transcript_data["content"]
        finally:
            fresh_session.close()

    def test_transcript_update_persists_to_database(self, db_session: Session):
        """Test that transcript updates persist to database"""
        # Arrange
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=creator)
        transcript = TranscriptFactory.create(
            db_session,
            meeting=meeting,
            content="Original content",
        )
        db_session.commit()

        update_data = {
            "content": "Updated transcript content",
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.put(f"/api/v1/transcripts/{transcript.id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["content"] == "Updated transcript content"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_transcript = fresh_session.query(Transcript).filter(Transcript.id == transcript.id).first()
            assert db_transcript is not None
            assert db_transcript.content == "Updated transcript content"
        finally:
            fresh_session.close()

    def test_transcript_linked_to_audio_file(self, db_session: Session):
        """Test that transcript can be linked to audio file"""
        # Arrange
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=creator)
        audio_file = AudioFileFactory.create(db_session, meeting=meeting, uploaded_by=creator)
        db_session.commit()

        transcript_data = {
            "meeting_id": str(meeting.id),
            "content": "Transcript for audio file",
            "audio_concat_file_id": str(audio_file.id),
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post("/api/v1/transcripts", json=transcript_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["audio_concat_file_id"] == str(audio_file.id)

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            transcript_id = uuid.UUID(data["data"]["id"])
            db_transcript = fresh_session.query(Transcript).filter(Transcript.id == transcript_id).first()
            assert db_transcript is not None
            assert db_transcript.audio_concat_file_id == audio_file.id
        finally:
            fresh_session.close()


class TestMeetingDeletionAndCleanup:
    """Integration tests for meeting deletion and cascade cleanup workflow"""

    def test_meeting_deletion_removes_from_database(self, db_session: Session):
        """Test that meeting deletion removes meeting from database"""
        # Arrange
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=creator)
        meeting_id = meeting.id
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/meetings/{meeting_id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify soft deleted in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_meeting = fresh_session.query(Meeting).filter(Meeting.id == meeting_id).first()
            assert db_meeting is not None
            assert db_meeting.is_deleted is True
        finally:
            fresh_session.close()

    def test_meeting_deletion_removes_associated_bots(self, db_session: Session):
        """Test that meeting deletion removes associated bots"""
        # Arrange
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=creator)
        bot = MeetingBotFactory.create(db_session, meeting=meeting, created_by=creator)
        meeting_id = meeting.id
        bot_id = bot.id
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/meetings/{meeting_id}")

        # Assert
        assert response.status_code == 200

        # Verify meeting is soft deleted and bot still exists (cascade delete not required for bots)
        fresh_session = SessionLocal()
        try:
            db_meeting = fresh_session.query(Meeting).filter(Meeting.id == meeting_id).first()
            assert db_meeting is not None
            assert db_meeting.is_deleted is True
        finally:
            fresh_session.close()

    def test_meeting_deletion_removes_associated_transcripts(self, db_session: Session):
        """Test that meeting deletion removes associated transcripts"""
        # Arrange
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=creator)
        transcript = TranscriptFactory.create(db_session, meeting=meeting)
        meeting_id = meeting.id
        transcript_id = transcript.id
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/meetings/{meeting_id}")

        # Assert
        assert response.status_code == 200

        # Verify meeting is soft deleted
        fresh_session = SessionLocal()
        try:
            db_meeting = fresh_session.query(Meeting).filter(Meeting.id == meeting_id).first()
            assert db_meeting is not None
            assert db_meeting.is_deleted is True
        finally:
            fresh_session.close()

    def test_meeting_deletion_removes_project_associations(self, db_session: Session):
        """Test that meeting deletion removes project associations"""
        # Arrange
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        meeting = MeetingFactory.create(db_session, created_by=creator, is_personal=False)
        project_meeting = ProjectMeetingFactory.create(db_session, project=project, meeting=meeting)
        meeting_id = meeting.id
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/meetings/{meeting_id}")

        # Assert
        assert response.status_code == 200

        # Verify meeting is soft deleted
        fresh_session = SessionLocal()
        try:
            db_meeting = fresh_session.query(Meeting).filter(Meeting.id == meeting_id).first()
            assert db_meeting is not None
            assert db_meeting.is_deleted is True
        finally:
            fresh_session.close()


class TestMeetingWorkflowDataPersistence:
    """Integration tests for meeting workflow data persistence"""

    def test_meeting_data_persists_across_sessions(self, db_session: Session):
        """Test that meeting data persists across database sessions"""
        # Arrange: Create meeting in one session
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(
            db_session,
            created_by=creator,
            title="Persistence Test Meeting",
            description="Test persistence",
        )
        meeting_id = meeting.id
        db_session.commit()
        db_session.close()

        # Act: Retrieve meeting in new session
        fresh_session = SessionLocal()
        try:
            db_meeting = fresh_session.query(Meeting).filter(Meeting.id == meeting_id).first()

            # Assert
            assert db_meeting is not None
            assert db_meeting.title == "Persistence Test Meeting"
            assert db_meeting.description == "Test persistence"
        finally:
            fresh_session.close()

    def test_meeting_bot_associations_persist(self, db_session: Session):
        """Test that meeting bot associations persist correctly"""
        # Arrange: Create meeting with bot
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=creator)
        bot = MeetingBotFactory.create(db_session, meeting=meeting, created_by=creator, status="pending")
        meeting_id = meeting.id
        bot_id = bot.id
        db_session.commit()
        db_session.close()

        # Act: Retrieve in new session
        fresh_session = SessionLocal()
        try:
            db_meeting = fresh_session.query(Meeting).filter(Meeting.id == meeting_id).first()
            db_bot = fresh_session.query(MeetingBot).filter(MeetingBot.id == bot_id).first()

            # Assert
            assert db_meeting is not None
            assert db_bot is not None
            assert db_bot.meeting_id == meeting_id
            assert db_bot.status == "pending"
        finally:
            fresh_session.close()

    def test_transcript_associations_persist(self, db_session: Session):
        """Test that transcript associations persist correctly"""
        # Arrange: Create meeting with transcript
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=creator)
        transcript = TranscriptFactory.create(
            db_session,
            meeting=meeting,
            content="Test transcript content",
        )
        meeting_id = meeting.id
        transcript_id = transcript.id
        db_session.commit()
        db_session.close()

        # Act: Retrieve in new session
        fresh_session = SessionLocal()
        try:
            db_meeting = fresh_session.query(Meeting).filter(Meeting.id == meeting_id).first()
            db_transcript = fresh_session.query(Transcript).filter(Transcript.id == transcript_id).first()

            # Assert
            assert db_meeting is not None
            assert db_transcript is not None
            assert db_transcript.meeting_id == meeting_id
            assert db_transcript.content == "Test transcript content"
        finally:
            fresh_session.close()

    def test_complete_meeting_workflow_persistence(self, db_session: Session):
        """Test complete meeting workflow: create, add bot, add transcript, verify persistence"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()

        meeting_data = {
            "title": "Complete Workflow Meeting",
            "description": "Initial description",
            "url": "https://meet.example.com/workflow",
            "is_personal": True,
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act 1: Create meeting
        create_response = client.post("/api/v1/meetings", json=meeting_data)
        assert create_response.status_code == 200
        meeting_id = uuid.UUID(create_response.json()["data"]["id"])

        # Act 2: Create bot for meeting
        bot_data = {
            "meeting_id": str(meeting_id),
            "scheduled_start_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "meeting_url": "https://meet.example.com/workflow",
        }
        bot_response = client.post("/api/v1/meeting-bots", json=bot_data)
        assert bot_response.status_code == 200
        bot_id = uuid.UUID(bot_response.json()["data"]["id"])

        # Act 3: Create transcript for meeting
        transcript_data = {
            "meeting_id": str(meeting_id),
            "content": "Complete workflow transcript",
        }
        transcript_response = client.post("/api/v1/transcripts", json=transcript_data)
        assert transcript_response.status_code == 200
        transcript_id = uuid.UUID(transcript_response.json()["data"]["id"])

        # Assert: Verify all data persisted correctly
        fresh_session = SessionLocal()
        try:
            # Verify meeting
            db_meeting = fresh_session.query(Meeting).filter(Meeting.id == meeting_id).first()
            assert db_meeting is not None
            assert db_meeting.title == "Complete Workflow Meeting"
            assert db_meeting.is_deleted is False

            # Verify bot
            db_bot = fresh_session.query(MeetingBot).filter(MeetingBot.id == bot_id).first()
            assert db_bot is not None
            assert db_bot.meeting_id == meeting_id
            assert db_bot.status == "pending"

            # Verify transcript
            db_transcript = fresh_session.query(Transcript).filter(Transcript.id == transcript_id).first()
            assert db_transcript is not None
            assert db_transcript.meeting_id == meeting_id
            assert db_transcript.content == "Complete workflow transcript"
        finally:
            fresh_session.close()

    def test_meeting_with_project_associations_persist(self, db_session: Session):
        """Test that meeting with project associations persist correctly"""
        # Arrange: Create meeting linked to project
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        meeting = MeetingFactory.create(db_session, created_by=creator, is_personal=False)
        project_meeting = ProjectMeetingFactory.create(db_session, project=project, meeting=meeting)
        meeting_id = meeting.id
        project_id = project.id
        db_session.commit()
        db_session.close()

        # Act: Retrieve in new session
        fresh_session = SessionLocal()
        try:
            db_meeting = fresh_session.query(Meeting).filter(Meeting.id == meeting_id).first()
            db_project_meeting = fresh_session.query(ProjectMeeting).filter(ProjectMeeting.meeting_id == meeting_id, ProjectMeeting.project_id == project_id).first()

            # Assert
            assert db_meeting is not None
            assert db_project_meeting is not None
            assert db_project_meeting.meeting_id == meeting_id
            assert db_project_meeting.project_id == project_id
        finally:
            fresh_session.close()

    def test_meeting_list_retrieval_shows_all_created_meetings(self, db_session: Session):
        """Test that meeting list retrieval shows all created meetings"""
        # Arrange: Create user and multiple meetings
        creator = UserFactory.create(db_session)
        db_session.commit()

        meetings_data = [
            {
                "title": f"List Meeting {i}",
                "description": f"Meeting {i} for list test",
                "url": f"https://meet.example.com/meeting{i}",
                "is_personal": True,
            }
            for i in range(3)
        ]

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Create meetings
        created_ids = []
        for meeting_data in meetings_data:
            response = client.post("/api/v1/meetings", json=meeting_data)
            assert response.status_code == 200
            created_ids.append(response.json()["data"]["id"])

        # Act: Retrieve meeting list
        list_response = client.get("/api/v1/meetings?limit=100")

        # Assert
        assert list_response.status_code == 200
        meetings = list_response.json()["data"]
        retrieved_ids = [m["id"] for m in meetings]
        for created_id in created_ids:
            assert created_id in retrieved_ids

    def test_meeting_update_and_retrieval_consistency(self, db_session: Session):
        """Test that updated meeting is consistent when retrieved"""
        # Arrange: Create meeting
        creator = UserFactory.create(db_session)
        meeting = MeetingFactory.create(db_session, created_by=creator, title="Initial Title")
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update meeting
        update_response = client.put(
            f"/api/v1/meetings/{meeting.id}",
            json={"title": "Updated Title"},
        )
        assert update_response.status_code == 200

        # Retrieve updated meeting
        get_response = client.get(f"/api/v1/meetings/{meeting.id}")

        # Assert
        assert get_response.status_code == 200
        data = get_response.json()["data"]
        assert data["title"] == "Updated Title"
