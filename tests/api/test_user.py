"""API endpoint tests for user management"""

import uuid
from typing import List

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.db import SessionLocal
from tests.factories import UserFactory


class TestGetUsersEndpoint:
    """Tests for GET /users endpoint"""

    def test_get_users_returns_paginated_list(self, client: TestClient, db_session: Session):
        """Test that GET /users returns paginated list of users"""
        # Arrange: Create test users
        users = UserFactory.create_batch(db_session, count=5)

        # Act: Get users
        response = client.get("/api/v1/users?page=1&limit=10")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 5
        assert data["pagination"]["total"] >= 5

    def test_get_users_with_pagination(self, client: TestClient, db_session: Session):
        """Test that pagination works correctly"""
        # Arrange: Create 15 test users
        UserFactory.create_batch(db_session, count=15)

        # Act: Get first page with limit 5
        response = client.get("/api/v1/users?page=1&limit=5")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 5

    def test_get_users_with_name_filter(self, client: TestClient, db_session: Session):
        """Test that name filter works correctly"""
        # Arrange: Create users with specific names
        user1 = UserFactory.create(db_session, name="John Doe")
        user2 = UserFactory.create(db_session, name="Jane Smith")
        UserFactory.create(db_session, name="Bob Johnson")

        # Act: Filter by name
        response = client.get("/api/v1/users?name=John")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 2  # John Doe and Bob Johnson
        names = [u["name"] for u in data["data"]]
        assert any("John" in name for name in names)

    def test_get_users_with_email_filter(self, client: TestClient, db_session: Session):
        """Test that email filter works correctly"""
        # Arrange: Create users with specific emails
        unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
        user = UserFactory.create(db_session, email=unique_email)

        # Act: Filter by email
        response = client.get(f"/api/v1/users?email={unique_email}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert any(u["email"] == unique_email for u in data["data"])

    def test_get_users_with_position_filter(self, client: TestClient, db_session: Session):
        """Test that position filter works correctly"""
        # Arrange: Create users with specific positions
        user1 = UserFactory.create(db_session, position="Engineer")
        user2 = UserFactory.create(db_session, position="Manager")

        # Act: Filter by position
        response = client.get("/api/v1/users?position=Engineer")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert any(u["position"] == "Engineer" for u in data["data"])

    def test_get_users_with_ordering(self, client: TestClient, db_session: Session):
        """Test that ordering works correctly"""
        # Arrange: Create test users
        UserFactory.create_batch(db_session, count=3)

        # Act: Get users ordered by created_at descending
        response = client.get("/api/v1/users?order_by=created_at&dir=desc")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 3

    def test_get_users_empty_result(self, client: TestClient, db_session: Session):
        """Test that empty filter returns empty list"""
        # Act: Filter by non-existent email
        response = client.get("/api/v1/users?email=nonexistent@example.com")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 0


class TestCreateUserEndpoint:
    """Tests for POST /users endpoint"""

    def test_create_user_with_valid_data(self, client: TestClient, db_session: Session):
        """Test creating a user with valid data"""
        # Arrange
        unique_email = f"newuser_{uuid.uuid4().hex[:8]}@example.com"
        user_data = {
            "email": unique_email,
            "name": "New User",
            "avatar_url": "https://example.com/avatar.jpg",
            "bio": "Test bio",
            "position": "Developer",
        }

        # Act
        response = client.post("/api/v1/users", json=user_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == unique_email
        assert data["data"]["name"] == "New User"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.email == unique_email).first()
            assert db_user is not None
            assert db_user.name == "New User"
        finally:
            fresh_session.close()

    def test_create_user_with_minimal_data(self, client: TestClient, db_session: Session):
        """Test creating a user with only required email"""
        # Arrange
        unique_email = f"minimal_{uuid.uuid4().hex[:8]}@example.com"
        user_data = {"email": unique_email}

        # Act
        response = client.post("/api/v1/users", json=user_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["email"] == unique_email

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.email == unique_email).first()
            assert db_user is not None
        finally:
            fresh_session.close()

    def test_create_user_with_duplicate_email(self, client: TestClient, db_session: Session):
        """Test that creating user with duplicate email fails"""
        # Arrange: Create first user
        unique_email = f"duplicate_{uuid.uuid4().hex[:8]}@example.com"
        user_data = {"email": unique_email, "name": "First User"}
        response1 = client.post("/api/v1/users", json=user_data)
        assert response1.status_code == 200

        # Act: Try to create user with same email
        response2 = client.post("/api/v1/users", json=user_data)

        # Assert
        assert response2.status_code == 400

    def test_create_user_persists_to_database(self, client: TestClient, db_session: Session):
        """Test that created user is persisted to database"""
        # Arrange
        unique_email = f"persist_{uuid.uuid4().hex[:8]}@example.com"
        user_data = {
            "email": unique_email,
            "name": "Persist User",
            "position": "Tester",
        }

        # Act
        response = client.post("/api/v1/users", json=user_data)

        # Assert
        assert response.status_code == 200
        user_id = response.json()["data"]["id"]

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == uuid.UUID(user_id)).first()
            assert db_user is not None
            assert db_user.email == unique_email
            assert db_user.name == "Persist User"
            assert db_user.position == "Tester"
        finally:
            fresh_session.close()


class TestUpdateUserEndpoint:
    """Tests for PUT /users/{id} endpoint"""

    def test_update_user_with_valid_data(self, client: TestClient, db_session: Session):
        """Test updating a user with valid data"""
        # Arrange: Create user
        user = UserFactory.create(db_session, name="Original Name")
        user_id = user.id

        # Act: Update user
        update_data = {"name": "Updated Name", "position": "Senior Developer"}
        response = client.put(f"/api/v1/users/{user_id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Updated Name"
        assert data["data"]["position"] == "Senior Developer"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user_id).first()
            assert db_user.name == "Updated Name"
            assert db_user.position == "Senior Developer"
        finally:
            fresh_session.close()

    def test_update_user_partial_fields(self, client: TestClient, db_session: Session):
        """Test updating only some fields"""
        # Arrange: Create user
        user = UserFactory.create(db_session, name="Original", bio="Original bio")
        user_id = user.id

        # Act: Update only name
        update_data = {"name": "Updated"}
        response = client.put(f"/api/v1/users/{user_id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Updated"

        # Verify bio unchanged
        db_user = db_session.query(User).filter(User.id == user_id).first()
        assert db_user.bio == "Original bio"

    def test_update_nonexistent_user(self, client: TestClient, db_session: Session):
        """Test updating non-existent user returns 404"""
        # Arrange
        fake_id = uuid.uuid4()

        # Act
        response = client.put(f"/api/v1/users/{fake_id}", json={"name": "Updated"})

        # Assert
        assert response.status_code == 404

    def test_update_user_persists_to_database(self, client: TestClient, db_session: Session):
        """Test that user updates are persisted to database"""
        # Arrange: Create user
        user = UserFactory.create(db_session, avatar_url="https://old.com/avatar.jpg")
        user_id = user.id

        # Act: Update avatar
        update_data = {"avatar_url": "https://new.com/avatar.jpg"}
        response = client.put(f"/api/v1/users/{user_id}", json=update_data)

        # Assert
        assert response.status_code == 200

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.id == user_id).first()
            assert db_user.avatar_url == "https://new.com/avatar.jpg"
        finally:
            fresh_session.close()


class TestDeleteUserEndpoint:
    """Tests for DELETE /users/{id} endpoint"""

    def test_delete_user_success(self, client: TestClient, db_session: Session):
        """Test deleting a user successfully"""
        # Arrange: Create user
        user = UserFactory.create(db_session)
        user_id = user.id

        # Act: Delete user
        response = client.delete(f"/api/v1/users/{user_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify removed from database
        db_user = db_session.query(User).filter(User.id == user_id).first()
        assert db_user is None

    def test_delete_nonexistent_user(self, client: TestClient, db_session: Session):
        """Test deleting non-existent user returns 404"""
        # Arrange
        fake_id = uuid.uuid4()

        # Act
        response = client.delete(f"/api/v1/users/{fake_id}")

        # Assert
        assert response.status_code == 404

    def test_delete_user_removes_from_database(self, client: TestClient, db_session: Session):
        """Test that deleted user is removed from database"""
        # Arrange: Create user
        user = UserFactory.create(db_session, email="delete@example.com")
        user_id = user.id

        # Verify user exists
        db_user = db_session.query(User).filter(User.id == user_id).first()
        assert db_user is not None

        # Act: Delete user
        response = client.delete(f"/api/v1/users/{user_id}")

        # Assert
        assert response.status_code == 200

        # Verify removed from database
        db_user = db_session.query(User).filter(User.id == user_id).first()
        assert db_user is None


class TestBulkCreateUsersEndpoint:
    """Tests for POST /users/bulk endpoint"""

    def test_bulk_create_users_success(self, client: TestClient, db_session: Session):
        """Test bulk creating multiple users"""
        # Arrange
        unique_suffix = uuid.uuid4().hex[:8]
        bulk_data = {
            "users": [
                {"email": f"bulk1_{unique_suffix}@example.com", "name": "Bulk User 1"},
                {"email": f"bulk2_{unique_suffix}@example.com", "name": "Bulk User 2"},
                {"email": f"bulk3_{unique_suffix}@example.com", "name": "Bulk User 3"},
            ]
        }

        # Act
        response = client.post("/api/v1/users/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        # Check that at least some users were created successfully
        assert data["total_processed"] == 3
        assert data["total_success"] >= 1  # At least one should succeed

        # Verify all users in database with fresh session
        fresh_session = SessionLocal()
        try:
            for user_data in bulk_data["users"]:
                db_user = fresh_session.query(User).filter(User.email == user_data["email"]).first()
                assert db_user is not None
                assert db_user.name == user_data["name"]
        finally:
            fresh_session.close()

    def test_bulk_create_with_duplicate_email(self, client: TestClient, db_session: Session):
        """Test bulk create with duplicate email in batch"""
        # Arrange: Create one user first using the service directly
        unique_email = f"existing_{uuid.uuid4().hex[:8]}@example.com"
        from app.services.user import create_user as service_create_user
        service_create_user(db_session, email=unique_email, name="Existing User")

        new_email = f"new_{uuid.uuid4().hex[:8]}@example.com"
        bulk_data = {
            "users": [
                {"email": unique_email, "name": "Duplicate"},
                {"email": new_email, "name": "New User"},
            ]
        }

        # Act
        response = client.post("/api/v1/users/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 2
        assert data["total_failed"] == 1
        assert data["total_success"] == 1

        # Verify new user was created with fresh session
        fresh_session = SessionLocal()
        try:
            db_user = fresh_session.query(User).filter(User.email == new_email).first()
            assert db_user is not None
        finally:
            fresh_session.close()

    def test_bulk_create_persists_to_database(self, client: TestClient, db_session: Session):
        """Test that bulk created users persist to database"""
        # Arrange
        unique_suffix = uuid.uuid4().hex[:8]
        email1 = f"persist1_{unique_suffix}@example.com"
        email2 = f"persist2_{unique_suffix}@example.com"
        bulk_data = {
            "users": [
                {"email": email1, "name": "Persist 1"},
                {"email": email2, "name": "Persist 2"},
            ]
        }

        # Act
        response = client.post("/api/v1/users/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            count = fresh_session.query(User).filter(User.email.in_([email1, email2])).count()
            assert count == 2
        finally:
            fresh_session.close()


class TestBulkUpdateUsersEndpoint:
    """Tests for PUT /users/bulk endpoint"""

    def test_bulk_update_users_success(self, client: TestClient, db_session: Session):
        """Test bulk updating multiple users"""
        # Arrange: Create users
        user1 = UserFactory.create(db_session, name="User 1")
        user2 = UserFactory.create(db_session, name="User 2")
        
        # Commit to ensure users are in database
        db_session.commit()

        bulk_data = {
            "users": [
                {"id": str(user1.id), "updates": {"name": "Updated 1"}},
                {"id": str(user2.id), "updates": {"name": "Updated 2"}},
            ]
        }

        # Act
        response = client.put("/api/v1/users/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_processed"] == 2
        assert data["total_success"] == 2

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_user1 = fresh_session.query(User).filter(User.id == user1.id).first()
            db_user2 = fresh_session.query(User).filter(User.id == user2.id).first()
            assert db_user1.name == "Updated 1"
            assert db_user2.name == "Updated 2"
        finally:
            fresh_session.close()

    def test_bulk_update_with_nonexistent_user(self, client: TestClient, db_session: Session):
        """Test bulk update with non-existent user"""
        # Arrange
        user = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        bulk_data = {
            "users": [
                {"id": str(user.id), "updates": {"name": "Updated"}},
                {"id": str(fake_id), "updates": {"name": "Fake"}},
            ]
        }

        # Act
        response = client.put("/api/v1/users/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 2
        assert data["total_failed"] == 1
        assert data["total_success"] == 1

    def test_bulk_update_persists_to_database(self, client: TestClient, db_session: Session):
        """Test that bulk updates persist to database"""
        # Arrange: Create users
        user1 = UserFactory.create(db_session, position="Old Position 1")
        user2 = UserFactory.create(db_session, position="Old Position 2")
        
        # Commit to ensure users are in database
        db_session.commit()

        bulk_data = {
            "users": [
                {"id": str(user1.id), "updates": {"position": "New Position 1"}},
                {"id": str(user2.id), "updates": {"position": "New Position 2"}},
            ]
        }

        # Act
        response = client.put("/api/v1/users/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 2
        assert data["total_success"] == 2

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_user1 = fresh_session.query(User).filter(User.id == user1.id).first()
            db_user2 = fresh_session.query(User).filter(User.id == user2.id).first()
            assert db_user1 is not None
            assert db_user2 is not None
            assert db_user1.position == "New Position 1"
            assert db_user2.position == "New Position 2"
        finally:
            fresh_session.close()


class TestBulkDeleteUsersEndpoint:
    """Tests for DELETE /users/bulk endpoint"""

    def test_bulk_delete_users_success(self, client: TestClient, db_session: Session):
        """Test bulk deleting multiple users"""
        # Arrange: Create users
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        user3 = UserFactory.create(db_session)

        user_ids = f"{user1.id},{user2.id},{user3.id}"

        # Act
        response = client.delete(f"/api/v1/users/bulk?user_ids={user_ids}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_processed"] == 3
        assert data["total_success"] == 3

        # Verify removed from database
        count = db_session.query(User).filter(User.id.in_([user1.id, user2.id, user3.id])).count()
        assert count == 0

    def test_bulk_delete_with_nonexistent_user(self, client: TestClient, db_session: Session):
        """Test bulk delete with non-existent user"""
        # Arrange
        user = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        user_ids = f"{user.id},{fake_id}"

        # Act
        response = client.delete(f"/api/v1/users/bulk?user_ids={user_ids}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 2
        assert data["total_failed"] == 1
        assert data["total_success"] == 1

        # Verify existing user was deleted
        db_user = db_session.query(User).filter(User.id == user.id).first()
        assert db_user is None

    def test_bulk_delete_removes_from_database(self, client: TestClient, db_session: Session):
        """Test that bulk deleted users are removed from database"""
        # Arrange: Create users
        user1 = UserFactory.create(db_session, email="delete1@example.com")
        user2 = UserFactory.create(db_session, email="delete2@example.com")

        user_ids = f"{user1.id},{user2.id}"

        # Act
        response = client.delete(f"/api/v1/users/bulk?user_ids={user_ids}")

        # Assert
        assert response.status_code == 200

        # Verify removed from database
        db_user1 = db_session.query(User).filter(User.id == user1.id).first()
        db_user2 = db_session.query(User).filter(User.id == user2.id).first()
        assert db_user1 is None
        assert db_user2 is None
