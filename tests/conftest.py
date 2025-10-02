import sys
import types

if "minio" not in sys.modules:
    minio_module = types.ModuleType("minio")

    class _StubMinio:
        def __init__(self, *args, **kwargs):
            pass

        def bucket_exists(self, bucket_name: str) -> bool:
            return False

        def make_bucket(self, bucket_name: str) -> None:
            pass

        def set_bucket_policy(self, bucket_name: str, policy: str) -> None:
            pass

        def put_object(self, *args, **kwargs):
            pass

        def get_object(self, *args, **kwargs):
            class _Response:
                def read(self) -> bytes:
                    return b""

            return _Response()

        def remove_object(self, *args, **kwargs):
            pass

        def stat_object(self, *args, **kwargs):
            pass

    minio_module.Minio = _StubMinio
    sys.modules["minio"] = minio_module
    minio_error = types.ModuleType("minio.error")

    class S3Error(Exception):
        pass

    minio_error.S3Error = S3Error
    sys.modules["minio.error"] = minio_error

if "chonkie" not in sys.modules:
    chonkie_module = types.ModuleType("chonkie")

    class GeminiEmbeddings:
        def __init__(self, api_key: str = ""):
            self.api_key = api_key

        def embed(self, query: str):
            return [0.0]

        def embed_batch(self, docs):
            return [[0.0] for _ in docs]

    class CodeChunker:
        def __init__(self, *args, **kwargs):
            pass

        def chunk(self, text: str):
            return [text]

    class SentenceChunker(CodeChunker):
        pass

    chonkie_module.GeminiEmbeddings = GeminiEmbeddings
    chonkie_module.CodeChunker = CodeChunker
    chonkie_module.SentenceChunker = SentenceChunker
    sys.modules["chonkie"] = chonkie_module

if "qdrant_client" not in sys.modules:
    qdrant_module = types.ModuleType("qdrant_client")

    class QdrantClient:
        def __init__(self, *args, **kwargs):
            self._collections = []

        def get_collections(self):
            class _Collections:
                def __init__(self, items):
                    self.collections = items

            return _Collections(self._collections)

        def create_collection(self, *args, **kwargs):
            return None

        def upsert(self, *args, **kwargs):
            return None

        def search(self, *args, **kwargs):
            return []

        def delete(self, *args, **kwargs):
            return None

        def get_collection(self, *args, **kwargs):
            return None

    qdrant_module.QdrantClient = QdrantClient
    sys.modules["qdrant_client"] = qdrant_module
    http_module = types.ModuleType("qdrant_client.http")
    sys.modules["qdrant_client.http"] = http_module
    qmodels_module = types.ModuleType("qdrant_client.http.models")

    class Distance:
        COSINE = "cosine"

    class VectorParams:
        def __init__(self, size: int, distance: str):
            self.size = size
            self.distance = distance

    class PointStruct:
        def __init__(self, id: str, vector, payload):
            self.id = id
            self.vector = vector
            self.payload = payload

    class MatchValue:
        def __init__(self, value):
            self.value = value

    class FieldCondition:
        def __init__(self, key: str, match):
            self.key = key
            self.match = match

    class Filter:
        def __init__(self, must=None):
            self.must = must or []

    class FilterSelector:
        def __init__(self, filter):
            self.filter = filter

    qmodels_module.Distance = Distance
    qmodels_module.VectorParams = VectorParams
    qmodels_module.PointStruct = PointStruct
    qmodels_module.MatchValue = MatchValue
    qmodels_module.FieldCondition = FieldCondition
    qmodels_module.Filter = Filter
    qmodels_module.FilterSelector = FilterSelector

    setattr(http_module, "models", qmodels_module)
    sys.modules["qdrant_client.http.models"] = qmodels_module
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

    print("ðŸ§¹ Starting database pruning...")

    try:
        # Delete all test data in reverse dependency order

        # Delete meeting-related data first
        deleted_meeting_bot_logs = db.query(MeetingBotLog).delete()
        print(f"âœ… Deleted {deleted_meeting_bot_logs} meeting bot logs")

        deleted_meeting_bots = db.query(MeetingBot).delete()
        print(f"âœ… Deleted {deleted_meeting_bots} meeting bots")

        deleted_meeting_notes = db.query(MeetingNote).delete()
        print(f"âœ… Deleted {deleted_meeting_notes} meeting notes")

        deleted_transcripts = db.query(Transcript).delete()
        print(f"âœ… Deleted {deleted_transcripts} transcripts")

        deleted_audio_files = db.query(AudioFile).delete()
        print(f"âœ… Deleted {deleted_audio_files} audio files")

        # Delete junction tables
        deleted_project_meetings = db.query(ProjectMeeting).delete()
        print(f"âœ… Deleted {deleted_project_meetings} project-meeting relationships")

        # Delete meetings
        deleted_meetings = db.query(Meeting).delete()
        print(f"âœ… Deleted {deleted_meetings} meetings")

        # Delete user_projects first (junction table)
        deleted_user_projects = db.query(UserProject).delete()
        print(f"âœ… Deleted {deleted_user_projects} user-project relationships")

        # Delete projects
        deleted_projects = db.query(Project).delete()
        print(f"âœ… Deleted {deleted_projects} projects")

        # Delete user devices
        deleted_devices = db.query(UserDevice).delete()
        print(f"âœ… Deleted {deleted_devices} user devices")

        # Delete user identities
        deleted_identities = db.query(UserIdentity).delete()
        print(f"âœ… Deleted {deleted_identities} user identities")

        # Delete users (including test user)
        deleted_users = db.query(User).delete()
        print(f"âœ… Deleted {deleted_users} users")

        # Commit all changes
        db.commit()

        print("ðŸŽ‰ Database pruning completed successfully!")
        print(f"ðŸ“Š Summary: {deleted_users} users, {deleted_projects} projects, {deleted_meetings} meetings, {deleted_user_projects} user-project relationships, {deleted_project_meetings} project-meeting relationships cleaned up")

    except Exception as e:
        print(f"âŒ Error during database pruning: {e}")
        db.rollback()
        raise


if __name__ == "__main__":
    """Allow running database pruning from command line"""
    print("ðŸ§¹ Running database pruning from command line...")
    db = SessionLocal()
    try:
        prune_database(db)
    finally:
        db.close()
