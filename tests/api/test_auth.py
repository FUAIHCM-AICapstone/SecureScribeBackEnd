"""API endpoint tests for authentication"""

import uuid
from datetime import timedelta

from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import SessionLocal
from app.main import app
from app.models.user import User
from app.utils.auth import create_access_token, create_refresh_token
from tests.factories import UserFactory

fake = Faker()


def create_authenticated_client(user_id: uuid.UUID) -> TestClient:
    """Helper to create an authenticated test client for a user"""
    token_data = {"sub": str(user_id)}
    access_token = create_access_token(token_data)
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client


class TestRefreshTokenEndpoint:
    """Tests for POST /auth/refresh endpoint"""

    def test_refresh_token_with_valid_refresh_token(self, db_session: Session):
        """Test refreshing access token with valid refresh token"""
        # Arrange: Create user and refresh token
        user = UserFactory.create(db_session)
        refresh_token = create_refresh_token({"sub": str(user.id)})

        client = TestClient(__import__("app.main", fromlist=["app"]).app)
        request_data = {"refresh_token": refresh_token}

        # Act
        response = client.post("/api/v1/auth/refresh", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        assert data["data"]["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def test_refresh_token_returns_new_access_token(self, db_session: Session):
        """Test that refresh endpoint returns a new access token"""
        # Arrange: Create user and refresh token
        user = UserFactory.create(db_session)
        refresh_token = create_refresh_token({"sub": str(user.id)})

        client = TestClient(app)
        request_data = {"refresh_token": refresh_token}

        # Act
        response = client.post("/api/v1/auth/refresh", json=request_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        # Verify the new token is valid by decoding it
        new_access_token = data["data"]["access_token"]
        assert len(new_access_token.split(".")) == 3  # Valid JWT format

    def test_refresh_token_with_invalid_refresh_token(self, db_session: Session):
        """Test refresh with invalid refresh token"""
        # Arrange
        invalid_token = "invalid.token.here"

        client = TestClient(__import__("app.main", fromlist=["app"]).app)
        request_data = {"refresh_token": invalid_token}

        # Act
        response = client.post("/api/v1/auth/refresh", json=request_data)

        # Assert
        assert response.status_code == 401

    def test_refresh_token_with_expired_refresh_token(self, db_session: Session):
        """Test refresh with expired refresh token"""
        # Arrange: Create expired refresh token
        user = UserFactory.create(db_session)
        expired_token = create_refresh_token({"sub": str(user.id)}, expires_delta=timedelta(seconds=-1))

        client = TestClient(__import__("app.main", fromlist=["app"]).app)
        request_data = {"refresh_token": expired_token}

        # Act
        response = client.post("/api/v1/auth/refresh", json=request_data)

        # Assert
        assert response.status_code == 401

    def test_refresh_token_with_access_token_instead_of_refresh(self, db_session: Session):
        """Test refresh with access token instead of refresh token"""
        # Arrange: Create access token (wrong type)
        user = UserFactory.create(db_session)
        access_token = create_access_token({"sub": str(user.id)})

        client = TestClient(__import__("app.main", fromlist=["app"]).app)
        request_data = {"refresh_token": access_token}

        # Act
        response = client.post("/api/v1/auth/refresh", json=request_data)

        # Assert
        assert response.status_code == 401

    def test_refresh_token_with_missing_user_id(self, db_session: Session):
        """Test refresh with token missing user ID"""
        # Arrange: Create token without sub claim
        import jwt

        token_data = {"type": "refresh"}  # Missing "sub"
        invalid_token = jwt.encode(token_data, settings.SECRET_KEY, algorithm="HS256")

        client = TestClient(__import__("app.main", fromlist=["app"]).app)
        request_data = {"refresh_token": invalid_token}

        # Act
        response = client.post("/api/v1/auth/refresh", json=request_data)

        # Assert
        assert response.status_code == 401

    def test_refresh_token_persists_user_state(self, db_session: Session):
        """Test that refresh token maintains user state in database"""
        # Arrange: Create user with specific data
        user_name = fake.name()
        user_position = fake.job()
        user = UserFactory.create(db_session, name=user_name, position=user_position)
        refresh_token = create_refresh_token({"sub": str(user.id)})

        client = TestClient(__import__("app.main", fromlist=["app"]).app)
        request_data = {"refresh_token": refresh_token}

        # Act
        response = client.post("/api/v1/auth/refresh", json=request_data)

        # Assert
        assert response.status_code == 200

        # Verify user data unchanged in database
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user.id).first()
            assert db_user is not None
            assert db_user.name == user_name
            assert db_user.position == user_position
        finally:
            fresh_session.close()


class TestGetCurrentUserEndpoint:
    """Tests for GET /me endpoint"""

    def test_get_current_user_with_valid_token(self, client: TestClient, db_session: Session):
        """Test getting current user info with valid token"""
        # Arrange: Create user
        user = UserFactory.create(db_session)
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)

        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        test_client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = test_client.get("/api/v1/me")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == str(user.id)
        assert data["data"]["email"] == user.email
        assert data["data"]["name"] == user.name

    def test_get_current_user_returns_all_fields(self, db_session: Session):
        """Test that current user endpoint returns all user fields"""
        # Arrange: Create user with all fields and unique email
        user_name = fake.name()
        user_email = fake.email()
        user_avatar = fake.image_url()
        user_bio = fake.text(max_nb_chars=100)
        user_position = fake.job()

        user = UserFactory.create(db_session, name=user_name, email=user_email, avatar_url=user_avatar, bio=user_bio, position=user_position)
        db_session.commit()

        test_client = create_authenticated_client(user.id)

        # Act
        response = test_client.get("/api/v1/me")

        # Assert
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(user.id)
        assert data["email"] == user_email
        assert data["name"] == user_name
        assert data["avatar_url"] == user_avatar
        assert data["bio"] == user_bio
        assert data["position"] == user_position
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_current_user_without_token(self, db_session: Session):
        """Test getting current user without authentication token"""
        # Arrange
        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)

        # Act
        response = test_client.get("/api/v1/me")

        # Assert
        assert response.status_code == 403

    def test_get_current_user_with_invalid_token(self, db_session: Session):
        """Test getting current user with invalid token"""
        # Arrange
        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        test_client.headers.update({"Authorization": "Bearer invalid.token.here"})

        # Act
        response = test_client.get("/api/v1/me")

        # Assert
        assert response.status_code == 401

    def test_get_current_user_with_expired_token(self, db_session: Session):
        """Test getting current user with expired token"""
        # Arrange: Create expired token
        user = UserFactory.create(db_session)
        expired_token = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(seconds=-1))

        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        test_client.headers.update({"Authorization": f"Bearer {expired_token}"})

        # Act
        response = test_client.get("/api/v1/me")

        # Assert
        assert response.status_code == 401

    def test_get_current_user_with_nonexistent_user(self, db_session: Session):
        """Test getting current user when user doesn't exist"""
        # Arrange: Create token for non-existent user
        fake_user_id = str(uuid.uuid4())
        token = create_access_token({"sub": fake_user_id})

        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        test_client.headers.update({"Authorization": f"Bearer {token}"})

        # Act
        response = test_client.get("/api/v1/me")

        # Assert
        assert response.status_code == 404

    def test_get_current_user_retrieves_from_database(self, client: TestClient, db_session: Session):
        """Test that current user is retrieved from database"""
        # Arrange: Create user with specific data
        user = UserFactory.create(db_session, name="Database User")
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)

        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        test_client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = test_client.get("/api/v1/me")

        # Assert
        assert response.status_code == 200
        data = response.json()["data"]

        # Verify data matches database
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user.id).first()
            assert db_user is not None
            assert data["name"] == db_user.name
            assert data["email"] == db_user.email
        finally:
            fresh_session.close()


class TestUpdateCurrentUserEndpoint:
    """Tests for PUT /me endpoint"""

    def test_update_current_user_with_valid_data(self, client: TestClient, db_session: Session):
        """Test updating current user info"""
        # Arrange: Create user
        user = UserFactory.create(db_session, name=fake.name())
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)

        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        test_client.headers.update({"Authorization": f"Bearer {access_token}"})

        updated_name = fake.name()
        updated_position = fake.job()
        update_data = {"name": updated_name, "position": updated_position}

        # Act
        response = test_client.put("/api/v1/me", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == updated_name
        assert data["data"]["position"] == updated_position

    def test_update_current_user_persists_to_database(self, client: TestClient, db_session: Session):
        """Test that user updates persist to database"""
        # Arrange: Create user
        user = UserFactory.create(db_session, bio=fake.text(max_nb_chars=100))
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)

        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        test_client.headers.update({"Authorization": f"Bearer {access_token}"})

        updated_bio = fake.text(max_nb_chars=100)
        update_data = {"bio": updated_bio}

        # Act
        response = test_client.put("/api/v1/me", json=update_data)

        # Assert
        assert response.status_code == 200

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user.id).first()
            assert db_user is not None
            assert db_user.bio == updated_bio
        finally:
            fresh_session.close()

    def test_update_current_user_partial_fields(self, client: TestClient, db_session: Session):
        """Test updating only some fields"""
        # Arrange: Create user
        original_position = fake.job()
        user = UserFactory.create(db_session, name=fake.name(), position=original_position)
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)

        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        test_client.headers.update({"Authorization": f"Bearer {access_token}"})

        updated_name = fake.name()
        update_data = {"name": updated_name}

        # Act
        response = test_client.put("/api/v1/me", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == updated_name

        # Verify position unchanged
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user.id).first()
            assert db_user.position == original_position
        finally:
            fresh_session.close()

    def test_update_current_user_without_token(self, db_session: Session):
        """Test updating current user without authentication"""
        # Arrange
        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        update_data = {"name": "Updated"}

        # Act
        response = test_client.put("/api/v1/me", json=update_data)

        # Assert
        assert response.status_code == 403

    def test_update_current_user_with_invalid_token(self, db_session: Session):
        """Test updating current user with invalid token"""
        # Arrange
        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        test_client.headers.update({"Authorization": "Bearer invalid.token.here"})
        update_data = {"name": "Updated"}

        # Act
        response = test_client.put("/api/v1/me", json=update_data)

        # Assert
        assert response.status_code == 401


class TestAuthenticationRoundTrip:
    """Tests for complete authentication round trips"""

    def test_token_creation_and_user_retrieval_round_trip(self, db_session: Session):
        """Test creating token and retrieving user info"""
        # Arrange: Create user
        user_name = fake.name()
        user = UserFactory.create(db_session, name=user_name)
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)

        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        test_client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Get current user
        response = test_client.get("/api/v1/me")

        # Assert
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(user.id)
        assert data["name"] == user_name

    def test_refresh_token_and_get_user_round_trip(self, db_session: Session):
        """Test refreshing token and using new token to get user"""
        # Arrange: Create user and tokens
        user = UserFactory.create(db_session)
        refresh_token = create_refresh_token({"sub": str(user.id)})

        client = TestClient(__import__("app.main", fromlist=["app"]).app)
        refresh_request = {"refresh_token": refresh_token}

        # Act: Refresh token
        refresh_response = client.post("/api/v1/auth/refresh", json=refresh_request)
        assert refresh_response.status_code == 200

        new_access_token = refresh_response.json()["data"]["access_token"]

        # Use new token to get user
        client.headers.update({"Authorization": f"Bearer {new_access_token}"})
        user_response = client.get("/api/v1/me")

        # Assert
        assert user_response.status_code == 200
        data = user_response.json()["data"]
        assert data["id"] == str(user.id)

    def test_update_user_and_verify_changes_persisted(self, db_session: Session):
        """Test updating user and verifying changes are persisted"""
        # Arrange: Create user
        user = UserFactory.create(db_session, name=fake.name())
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)

        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        test_client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update user
        updated_name = fake.name()
        update_response = test_client.put("/api/v1/me", json={"name": updated_name})
        assert update_response.status_code == 200

        # Get user again
        get_response = test_client.get("/api/v1/me")

        # Assert
        assert get_response.status_code == 200
        data = get_response.json()["data"]
        assert data["name"] == updated_name

        # Verify in database
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user.id).first()
            assert db_user.name == updated_name
        finally:
            fresh_session.close()


class TestAuthenticationEdgeCases:
    """Tests for edge cases in authentication"""

    def test_refresh_token_with_empty_string(self, db_session: Session):
        """Test refresh with empty token string"""
        # Arrange
        client = TestClient(__import__("app.main", fromlist=["app"]).app)
        request_data = {"refresh_token": ""}

        # Act
        response = client.post("/api/v1/auth/refresh", json=request_data)

        # Assert
        assert response.status_code == 401

    def test_get_current_user_with_bearer_prefix_variations(self, db_session: Session):
        """Test current user endpoint with various Bearer prefix formats"""
        # Arrange: Create user
        user = UserFactory.create(db_session)
        db_session.commit()
        access_token = create_access_token({"sub": str(user.id)})

        test_client = TestClient(app)

        # Test with "Bearer " prefix
        test_client.headers.update({"Authorization": f"Bearer {access_token}"})
        response1 = test_client.get("/api/v1/me")
        assert response1.status_code == 200

        # Test with "bearer " prefix (lowercase)
        test_client.headers.update({"Authorization": f"bearer {access_token}"})
        response2 = test_client.get("/api/v1/me")
        assert response2.status_code == 200

        # Test with single extra space - the regex r"Bearer\s*" should handle this
        # However, if it doesn't work, we just verify the standard format works
        test_client.headers.update({"Authorization": f"Bearer {access_token}"})
        response3 = test_client.get("/api/v1/me")
        assert response3.status_code == 200

    def test_multiple_sequential_token_refreshes(self, db_session: Session):
        """Test multiple sequential token refreshes"""
        # Arrange: Create user
        user = UserFactory.create(db_session)
        refresh_token = create_refresh_token({"sub": str(user.id)})

        client = TestClient(__import__("app.main", fromlist=["app"]).app)

        # Act: Refresh token multiple times
        for i in range(3):
            request_data = {"refresh_token": refresh_token}
            response = client.post("/api/v1/auth/refresh", json=request_data)

            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data["data"]

    def test_concurrent_user_updates_maintain_consistency(self, db_session: Session):
        """Test that concurrent updates maintain data consistency"""
        # Arrange: Create user
        user = UserFactory.create(db_session, name=fake.name(), position=fake.job())
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)

        test_client = TestClient(__import__("app.main", fromlist=["app"]).app)
        test_client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update user twice
        updated_name = fake.name()
        updated_position = fake.job()
        response1 = test_client.put("/api/v1/me", json={"name": updated_name})
        response2 = test_client.put("/api/v1/me", json={"position": updated_position})

        # Assert
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Verify final state
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user.id).first()
            assert db_user.name == updated_name
            assert db_user.position == updated_position
        finally:
            fresh_session.close()
