import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal, create_tables
from app.main import app
from app.services.user import create_user
from app.utils.auth import create_access_token

# Configure logging to ignore warnings
logging.getLogger().setLevel(logging.ERROR)
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
logging.getLogger("fastapi").setLevel(logging.ERROR)
logging.getLogger("uvicorn").setLevel(logging.ERROR)


@pytest.fixture(scope="session")
def db():
    """Create test database session"""
    # Create all tables
    create_tables()

    # Create a session
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def test_user(db: Session):
    """Create a test user for authentication"""
    # Check if test user already exists
    from app.models.user import User

    test_email = "test@example.com"
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
        print(
            f"📊 Summary: {deleted_users} users, {deleted_projects} projects, "
            f"{deleted_meetings} meetings, {deleted_user_projects} user-project relationships, "
            f"{deleted_project_meetings} project-meeting relationships cleaned up"
        )

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
