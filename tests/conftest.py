import logging
import sys
import warnings
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal, create_tables
from app.main import app
from app.services.user import create_user
from app.utils.auth import create_access_token

# Ensure application package is importable during tests
# This MUST be done before any app imports
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Mock problematic imports before importing app
sys.modules["chonkie"] = MagicMock()

# Mock Redis before importing app to prevent connection errors
sys.modules["redis"] = MagicMock()
sys.modules["redis.asyncio"] = MagicMock()

# Configure logging to ignore warnings
logging.getLogger().setLevel(logging.ERROR)
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
logging.getLogger("fastapi").setLevel(logging.ERROR)
logging.getLogger("uvicorn").setLevel(logging.ERROR)

# Ignore all warnings in tests
warnings.filterwarnings("ignore")
pytest.mark.filterwarnings("ignore")


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Setup test database - runs once per session"""
    # Create all tables
    create_tables()
    yield
    # Cleanup is handled by database itself


def _cleanup_test_data(session: Session):
    """Clean up all test data from database"""
    from app.models.chat import ChatMessage, Conversation
    from app.models.file import File
    from app.models.integration import Integration
    from app.models.meeting import AudioFile, Meeting, MeetingBot, MeetingBotLog, MeetingNote, ProjectMeeting, Transcript
    from app.models.notification import Notification
    from app.models.project import Project, UserProject
    from app.models.task import Task, TaskProject
    from app.models.user import User, UserDevice, UserIdentity

    try:
        # Delete in reverse dependency order
        session.query(ChatMessage).delete()
        session.query(Conversation).delete()
        session.query(MeetingBotLog).delete()
        session.query(MeetingBot).delete()
        session.query(MeetingNote).delete()
        session.query(Transcript).delete()
        session.query(AudioFile).delete()
        session.query(ProjectMeeting).delete()
        session.query(Meeting).delete()
        session.query(UserProject).delete()
        session.query(TaskProject).delete()
        session.query(Task).delete()
        session.query(File).delete()
        session.query(Notification).delete()
        session.query(Integration).delete()
        session.query(UserDevice).delete()
        session.query(UserIdentity).delete()
        session.query(Project).delete()
        session.query(User).filter(User.email != "pytest_auth_user@example.com").delete()
        session.commit()
    except Exception:
        session.rollback()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a database session for each test with automatic cleanup"""
    # Create a new session for each test
    session = SessionLocal()

    # Clean up before test
    _cleanup_test_data(session)

    try:
        yield session
    finally:
        # Clean up after test
        # _cleanup_test_data(session)
        session.close()


@pytest.fixture(scope="session")
def test_user():
    """Create a test user for authentication"""
    # Check if test user already exists
    from app.models.user import User

    db = SessionLocal()
    try:
        test_email = "pytest_auth_user@example.com"
        user = db.query(User).filter(User.email == test_email).first()

        if not user:
            # Create test user
            user_data = {
                "email": test_email,
                "name": "Test User",
                "avatar_url": "https://example.com/avatar.jpg",
                "bio": "Test user for automated testing",
                "position": "Software Engineer",
            }
            user = create_user(db, **user_data)

        return user
    finally:
        db.close()


@pytest.fixture(scope="session")
def auth_token(test_user):
    """Create access token for test user"""
    token_data = {"sub": str(test_user.id)}
    access_token = create_access_token(token_data)
    return access_token


@pytest.fixture
def client(auth_token):
    """Test client with authentication"""
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {auth_token}"})
    return client


@pytest.fixture
def unauthenticated_client():
    """Test client without authentication"""
    return TestClient(app)


# Mock factories for external services
@pytest.fixture
def mock_minio_client():
    """Mock MinIO client"""
    from tests.mocks import create_mock_minio_client

    return create_mock_minio_client()


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client"""
    from tests.mocks import create_mock_qdrant_client

    return create_mock_qdrant_client()


@pytest.fixture
def mock_redis_client():
    """Mock Redis client"""
    from tests.mocks import create_mock_redis_client

    return create_mock_redis_client()


def prune_database(db: Session):
    """Prune all test data from database"""
    from app.models.meeting import (
        AudioFile,
        Meeting,
        MeetingBot,
        MeetingBotLog,
        MeetingNote,
        ProjectMeeting,
        Transcript,
    )
    from app.models.project import Project, UserProject
    from app.models.user import User, UserDevice, UserIdentity

    print("🧹 Starting database pruning...")

    try:
        # Delete all test data in reverse dependency order

        # Delete meeting-related data first
        deleted_meeting_bot_logs = db.query(MeetingBotLog).delete()
        print(f"✅ Deleted {deleted_meeting_bot_logs} meeting bot logs")

        deleted_meeting_bots = db.query(MeetingBot).delete()
        print(f"✅ Deleted {deleted_meeting_bots} meeting bots")

        deleted_meeting_notes = db.query(MeetingNote).delete()
        print(f"✅ Deleted {deleted_meeting_notes} meeting notes")

        deleted_transcripts = db.query(Transcript).delete()
        print(f"✅ Deleted {deleted_transcripts} transcripts")

        deleted_audio_files = db.query(AudioFile).delete()
        print(f"✅ Deleted {deleted_audio_files} audio files")

        # Delete junction tables
        deleted_project_meetings = db.query(ProjectMeeting).delete()
        print(f"✅ Deleted {deleted_project_meetings} project-meeting relationships")

        # Delete meetings
        deleted_meetings = db.query(Meeting).delete()
        print(f"✅ Deleted {deleted_meetings} meetings")

        # Delete user_projects first (junction table)
        deleted_user_projects = db.query(UserProject).delete()
        print(f"✅ Deleted {deleted_user_projects} user-project relationships")

        # Delete projects
        deleted_projects = db.query(Project).delete()
        print(f"✅ Deleted {deleted_projects} projects")

        # Delete user devices
        deleted_devices = db.query(UserDevice).delete()
        print(f"✅ Deleted {deleted_devices} user devices")

        # Delete user identities
        deleted_identities = db.query(UserIdentity).delete()
        print(f"✅ Deleted {deleted_identities} user identities")

        # Delete users (including test user)
        deleted_users = db.query(User).delete()
        print(f"✅ Deleted {deleted_users} users")

        # Commit all changes
        db.commit()

        print("🎉 Database pruning completed successfully!")
        print(f"📊 Summary: {deleted_users} users, {deleted_projects} projects, {deleted_meetings} meetings, {deleted_user_projects} user-project relationships, {deleted_project_meetings} project-meeting relationships cleaned up")

    except Exception as e:
        print(f"❌ Error during database pruning: {e}")
        db.rollback()
        raise


if __name__ == "__main__":
    """Allow running database pruning from command line"""
    print("🧹 Running database pruning from command line...")
    db = SessionLocal()
    try:
        prune_database(db)
    finally:
        db.close()
