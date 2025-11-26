"""Integration tests for user workflows"""

import uuid
from datetime import timedelta

from faker import Faker
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models.user import User
from app.utils.auth import create_access_token, create_refresh_token
from tests.factories import UserFactory

fake = Faker()


class TestUserRegistrationAndProfileSetup:
    """Integration tests for user registration and profile setup workflow"""

    def test_user_registration_creates_database_record(self, db_session: Session):
        """Test that user registration creates a record in the database"""
        # Arrange
        user_data = {
            "email": f"newuser_{uuid.uuid4().hex[:8]}@example.com",
            "name": fake.name(),
            "avatar_url": fake.url(),
            "bio": fake.paragraph(),
            "position": fake.job(),
        }
        client = TestClient(app)

        # Act
        response = client.post("/api/v1/users", json=user_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == user_data["email"]
        assert data["data"]["name"] == user_data["name"]

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.email == user_data["email"]).first()
            assert db_user is not None
            assert db_user.name == user_data["name"]
            assert db_user.position == user_data["position"]
        finally:
            fresh_session.close()

    def test_user_registration_with_all_fields(self, db_session: Session):
        """Test user registration with all profile fields"""
        # Arrange
        user_data = {
            "email": f"fullprofile_{uuid.uuid4().hex[:8]}@example.com",
            "name": fake.name(),
            "avatar_url": fake.url(),
            "bio": fake.paragraph(),
            "position": fake.job(),
        }
        client = TestClient(app)

        # Act
        response = client.post("/api/v1/users", json=user_data)

        # Assert
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["email"] == user_data["email"]
        assert data["name"] == user_data["name"]
        assert data["avatar_url"] == user_data["avatar_url"]
        assert data["bio"] == user_data["bio"]
        assert data["position"] == user_data["position"]

    def test_user_registration_prevents_duplicate_email(self, db_session: Session):
        """Test that duplicate email registration is prevented"""
        # Arrange: Create first user
        user1 = UserFactory.create(db_session)
        db_session.commit()

        # Try to create second user with same email
        user_data = {
            "email": user1.email,
            "name": fake.name(),
            "avatar_url": fake.url(),
            "bio": fake.paragraph(),
            "position": fake.job(),
        }
        client = TestClient(app)

        # Act
        response = client.post("/api/v1/users", json=user_data)

        # Assert
        assert response.status_code == 400

    def test_user_profile_setup_persists_all_data(self, db_session: Session):
        """Test that all profile data persists correctly"""
        # Arrange
        user_data = {
            "email": f"persist_{uuid.uuid4().hex[:8]}@example.com",
            "name": fake.name(),
            "avatar_url": fake.url(),
            "bio": fake.paragraph(),
            "position": fake.job(),
        }
        client = TestClient(app)

        # Act: Create user
        response = client.post("/api/v1/users", json=user_data)
        assert response.status_code == 200
        created_user_id = response.json()["data"]["id"]

        # Verify persistence with fresh session
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == uuid.UUID(created_user_id)).first()
            assert db_user is not None
            assert db_user.email == user_data["email"]
            assert db_user.name == user_data["name"]
            assert db_user.avatar_url == user_data["avatar_url"]
            assert db_user.bio == user_data["bio"]
            assert db_user.position == user_data["position"]
        finally:
            fresh_session.close()

    def test_user_registration_returns_user_id(self, db_session: Session):
        """Test that registration returns a valid user ID"""
        # Arrange
        user_data = {
            "email": f"userid_{uuid.uuid4().hex[:8]}@example.com",
            "name": fake.name(),
            "avatar_url": fake.url(),
            "bio": fake.paragraph(),
            "position": fake.job(),
        }
        client = TestClient(app)

        # Act
        response = client.post("/api/v1/users", json=user_data)

        # Assert
        assert response.status_code == 200
        user_id = response.json()["data"]["id"]
        assert user_id is not None
        # Verify it's a valid UUID
        uuid.UUID(user_id)


class TestUserAuthenticationAndTokenRefresh:
    """Integration tests for user authentication and token refresh workflow"""

    def test_user_authentication_creates_valid_token(self, db_session: Session):
        """Test that user authentication creates a valid token"""
        # Arrange: Create user
        user = UserFactory.create(db_session)
        db_session.commit()

        # Create token
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)

        # Act: Use token to access protected endpoint
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})
        response = client.get("/api/v1/me")

        # Assert
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(user.id)

    def test_token_refresh_maintains_user_state(self, db_session: Session):
        """Test that token refresh maintains user state in database"""
        # Arrange: Create user with specific data
        user = UserFactory.create(db_session, name="Token Refresh User", position="Engineer")
        db_session.commit()

        refresh_token = create_refresh_token({"sub": str(user.id)})

        # Act: Refresh token
        client = TestClient(app)
        response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})

        # Assert
        assert response.status_code == 200
        new_access_token = response.json()["data"]["access_token"]

        # Verify user state unchanged in database
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user.id).first()
            assert db_user is not None
            assert db_user.name == "Token Refresh User"
            assert db_user.position == "Engineer"
        finally:
            fresh_session.close()

        # Verify new token works
        client.headers.update({"Authorization": f"Bearer {new_access_token}"})
        me_response = client.get("/api/v1/me")
        assert me_response.status_code == 200

    def test_authentication_round_trip_with_token_refresh(self, db_session: Session):
        """Test complete authentication round trip: create token, refresh, use new token"""
        # Arrange: Create user
        user = UserFactory.create(db_session)
        db_session.commit()

        refresh_token = create_refresh_token({"sub": str(user.id)})
        client = TestClient(app)

        # Act 1: Refresh token
        refresh_response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        assert refresh_response.status_code == 200

        new_access_token = refresh_response.json()["data"]["access_token"]

        # Act 2: Use new token to get user
        client.headers.update({"Authorization": f"Bearer {new_access_token}"})
        user_response = client.get("/api/v1/me")

        # Assert
        assert user_response.status_code == 200
        data = user_response.json()["data"]
        assert data["id"] == str(user.id)

    def test_multiple_sequential_token_refreshes_maintain_consistency(self, db_session: Session):
        """Test multiple sequential token refreshes maintain data consistency"""
        # Arrange: Create user
        user = UserFactory.create(db_session, name="Multi Refresh User")
        db_session.commit()

        refresh_token = create_refresh_token({"sub": str(user.id)})
        client = TestClient(app)

        # Act: Refresh token multiple times
        for i in range(3):
            response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
            assert response.status_code == 200

        # Assert: Verify user state unchanged
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user.id).first()
            assert db_user is not None
            assert db_user.name == "Multi Refresh User"
        finally:
            fresh_session.close()

    def test_authentication_with_expired_token_fails(self, db_session: Session):
        """Test that expired token fails authentication"""
        # Arrange: Create user with expired token
        user = UserFactory.create(db_session)
        db_session.commit()

        expired_token = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(seconds=-1))

        # Act
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {expired_token}"})
        response = client.get("/api/v1/me")

        # Assert
        assert response.status_code == 401

    def test_authentication_persists_user_lookup_in_database(self, db_session: Session):
        """Test that authentication performs user lookup in database"""
        # Arrange: Create user
        user = UserFactory.create(db_session, email=f"auth_lookup_{uuid.uuid4().hex[:8]}@example.com")
        db_session.commit()

        access_token = create_access_token({"sub": str(user.id)})

        # Act
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})
        response = client.get("/api/v1/me")

        # Assert
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["email"] == user.email


class TestUserProfileUpdatesAndDeletion:
    """Integration tests for user profile updates and deletion workflow"""

    def test_user_profile_update_persists_to_database(self, db_session: Session):
        """Test that profile updates persist to database"""
        # Arrange: Create user
        user = UserFactory.create(db_session, name="Original Name", position="Developer")
        db_session.commit()

        access_token = create_access_token({"sub": str(user.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update profile
        update_data = {"name": "Updated Name", "position": "Senior Developer"}
        response = client.put("/api/v1/me", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == "Updated Name"
        assert data["position"] == "Senior Developer"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user.id).first()
            assert db_user is not None
            assert db_user.name == "Updated Name"
            assert db_user.position == "Senior Developer"
        finally:
            fresh_session.close()

    def test_user_profile_partial_update(self, db_session: Session):
        """Test updating only some profile fields"""
        # Arrange: Create user
        user = UserFactory.create(db_session, name="Original", position="Engineer", bio="Original bio")
        db_session.commit()

        access_token = create_access_token({"sub": str(user.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update only name
        response = client.put("/api/v1/me", json={"name": "Updated"})

        # Assert
        assert response.status_code == 200

        # Verify other fields unchanged
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user.id).first()
            assert db_user.name == "Updated"
            assert db_user.position == "Engineer"
            assert db_user.bio == "Original bio"
        finally:
            fresh_session.close()

    def test_user_deletion_removes_from_database(self, db_session: Session):
        """Test that user deletion removes user from database"""
        # Arrange: Create user
        user = UserFactory.create(db_session)
        user_id = user.id
        db_session.commit()

        client = TestClient(app)

        # Act: Delete user
        response = client.delete(f"/api/v1/users/{user_id}")

        # Assert
        assert response.status_code == 200

        # Verify deleted from database with fresh session
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user_id).first()
            assert db_user is None
        finally:
            fresh_session.close()

    def test_user_deletion_via_api_endpoint(self, db_session: Session):
        """Test user deletion through API endpoint"""
        # Arrange: Create user
        user = UserFactory.create(db_session, email=f"delete_{uuid.uuid4().hex[:8]}@example.com")
        user_id = user.id
        db_session.commit()

        client = TestClient(app)

        # Act: Delete user
        response = client.delete(f"/api/v1/users/{user_id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deletion
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user_id).first()
            assert db_user is None
        finally:
            fresh_session.close()

    def test_user_profile_update_and_retrieval_consistency(self, db_session: Session):
        """Test that updated profile is consistent when retrieved"""
        # Arrange: Create user
        user = UserFactory.create(db_session, name="Initial")
        db_session.commit()

        access_token = create_access_token({"sub": str(user.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update profile
        update_response = client.put("/api/v1/me", json={"name": "Updated"})
        assert update_response.status_code == 200

        # Retrieve updated profile
        get_response = client.get("/api/v1/me")

        # Assert
        assert get_response.status_code == 200
        data = get_response.json()["data"]
        assert data["name"] == "Updated"

    def test_multiple_sequential_profile_updates(self, db_session: Session):
        """Test multiple sequential profile updates maintain consistency"""
        # Arrange: Create user
        user = UserFactory.create(db_session, name="Initial", position="Developer")
        db_session.commit()

        access_token = create_access_token({"sub": str(user.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update profile multiple times
        updates = [
            {"name": "Update1"},
            {"position": "Senior"},
            {"bio": "New bio"},
        ]

        for update in updates:
            response = client.put("/api/v1/me", json=update)
            assert response.status_code == 200

        # Assert: Verify all updates applied
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user.id).first()
            assert db_user.name == "Update1"
            assert db_user.position == "Senior"
            assert db_user.bio == "New bio"
        finally:
            fresh_session.close()


class TestUserWorkflowDataPersistence:
    """Integration tests for user workflow data persistence"""

    def test_user_data_persists_across_sessions(self, db_session: Session):
        """Test that user data persists across database sessions"""
        # Arrange: Create user in one session
        user = UserFactory.create(db_session, email=f"persist_{uuid.uuid4().hex[:8]}@example.com", name="Persistence Test", position="Engineer")
        user_id = user.id
        db_session.commit()
        db_session.close()

        # Act: Retrieve user in new session
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user_id).first()

            # Assert
            assert db_user is not None
            assert db_user.name == "Persistence Test"
            assert db_user.position == "Engineer"
        finally:
            fresh_session.close()

    def test_user_creation_and_retrieval_workflow(self, db_session: Session):
        """Test complete user creation and retrieval workflow"""
        # Arrange
        user_data = {
            "email": f"workflow_{uuid.uuid4().hex[:8]}@example.com",
            "name": "Workflow User",
            "avatar_url": "https://example.com/avatar.jpg",
            "bio": "Workflow test",
            "position": "Developer",
        }
        client = TestClient(app)

        # Act 1: Create user
        create_response = client.post("/api/v1/users", json=user_data)
        assert create_response.status_code == 200
        created_user_id = create_response.json()["data"]["id"]

        # Act 2: Retrieve user via API
        get_response = client.get(f"/api/v1/users?email={user_data['email']}")

        # Assert
        assert get_response.status_code == 200
        users = get_response.json()["data"]
        assert len(users) > 0
        assert any(u["id"] == created_user_id for u in users)

    def test_user_registration_authentication_update_workflow(self, db_session: Session):
        """Test complete workflow: register, authenticate, update"""
        # Arrange
        user_data = {
            "email": f"complete_{uuid.uuid4().hex[:8]}@example.com",
            "name": "Complete Workflow",
            "avatar_url": "https://example.com/avatar.jpg",
            "bio": "Complete test",
            "position": "Developer",
        }
        client = TestClient(app)

        # Act 1: Register user
        register_response = client.post("/api/v1/users", json=user_data)
        assert register_response.status_code == 200
        user_id = register_response.json()["data"]["id"]

        # Act 2: Authenticate (create token)
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == uuid.UUID(user_id)).first()
            access_token = create_access_token({"sub": str(db_user.id)})
        finally:
            fresh_session.close()

        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act 3: Update profile
        update_response = client.put("/api/v1/me", json={"name": "Updated Complete"})
        assert update_response.status_code == 200

        # Act 4: Retrieve updated profile
        get_response = client.get("/api/v1/me")

        # Assert
        assert get_response.status_code == 200
        data = get_response.json()["data"]
        assert data["name"] == "Updated Complete"

        # Verify in database
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == uuid.UUID(user_id)).first()
            assert db_user.name == "Updated Complete"
        finally:
            fresh_session.close()

    def test_user_list_retrieval_shows_all_created_users(self, db_session: Session):
        """Test that user list retrieval shows all created users"""
        # Arrange: Create multiple users
        users_data = [
            {
                "email": f"list_{i}_{uuid.uuid4().hex[:8]}@example.com",
                "name": f"List User {i}",
                "avatar_url": "https://example.com/avatar.jpg",
                "bio": f"User {i}",
                "position": "Developer",
            }
            for i in range(3)
        ]

        client = TestClient(app)

        # Act: Create users
        created_ids = []
        for user_data in users_data:
            response = client.post("/api/v1/users", json=user_data)
            assert response.status_code == 200
            created_ids.append(response.json()["data"]["id"])

        # Act: Retrieve user list
        list_response = client.get("/api/v1/users?limit=100")

        # Assert
        assert list_response.status_code == 200
        users = list_response.json()["data"]
        retrieved_ids = [u["id"] for u in users]
        for created_id in created_ids:
            assert created_id in retrieved_ids
