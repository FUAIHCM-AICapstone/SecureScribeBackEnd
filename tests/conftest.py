import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal, create_tables
from app.main import app
from app.services.user import create_user
from app.utils.auth import create_access_token


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
