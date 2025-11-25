"""Unit tests for user service functions"""

import uuid

import pytest
from faker import Faker
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.constants.messages import MessageDescriptions
from app.models.user import User
from app.services.user import (
    bulk_create_users,
    bulk_delete_users,
    bulk_update_users,
    check_email_exists,
    create_user,
    delete_user,
    get_user_by_id,
    get_users,
    update_user,
)
from tests.factories import UserFactory

fake = Faker()


class TestCreateUser:
    """Tests for create_user function"""

    def test_create_user_success(self, db_session: Session):
        """Test creating a user with valid data"""
        user_data = {
            "email": fake.email(),
            "name": fake.name(),
            "avatar_url": fake.image_url(),
            "bio": fake.text(max_nb_chars=100),
            "position": fake.job(),
        }

        user = create_user(db_session, **user_data)

        assert user.id is not None
        assert user.email == user_data["email"]
        assert user.name == user_data["name"]
        assert user.avatar_url == user_data["avatar_url"]
        assert user.bio == user_data["bio"]
        assert user.position == user_data["position"]
        assert user.created_at is not None

    def test_create_user_duplicate_email(self, db_session: Session):
        """Test creating a user with duplicate email raises error"""
        duplicate_email = fake.email()
        # Create first user
        user_data = {"email": duplicate_email, "name": fake.name()}
        user1 = create_user(db_session, **user_data)
        assert user1.id is not None

        # Try to create second user with same email
        duplicate_data = {"email": duplicate_email, "name": fake.name()}
        with pytest.raises(HTTPException) as exc_info:
            create_user(db_session, **duplicate_data)

        # Service now validates email uniqueness before database operations
        assert exc_info.value.status_code == 400
        assert "already exists" in str(exc_info.value.detail).lower()

    def test_create_user_minimal_data(self, db_session: Session):
        """Test creating a user with only required email field"""
        minimal_email = fake.email()
        user = create_user(db_session, email=minimal_email)

        assert user.email == minimal_email
        assert user.name is None
        assert user.avatar_url is None

    def test_create_user_with_actor(self, db_session: Session):
        """Test creating a user with actor_user_id for audit"""
        actor_email = fake.email()
        actor_id = uuid.uuid4()
        user = create_user(db_session, actor_user_id=actor_id, email=actor_email)

        assert user.email == actor_email
        assert user.id is not None


class TestUpdateUser:
    """Tests for update_user function"""

    def test_update_user_success(self, db_session: Session):
        """Test updating a user with valid data"""
        original_name = fake.name()
        user = UserFactory.create(db_session, name=original_name)

        updated_name = fake.name()
        updated_bio = fake.text(max_nb_chars=100)
        updated_user = update_user(
            db_session,
            user.id,
            name=updated_name,
            bio=updated_bio,
        )

        assert updated_user.name == updated_name
        assert updated_user.bio == updated_bio
        assert updated_user.id == user.id

    def test_update_user_not_found(self, db_session: Session):
        """Test updating non-existent user raises error"""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            update_user(db_session, fake_id, name="New Name")

        assert exc_info.value.status_code == 404

    def test_update_user_partial_fields(self, db_session: Session):
        """Test updating only some fields"""
        original_name = fake.name()
        original_bio = fake.text(max_nb_chars=100)
        original_position = fake.job()
        user = UserFactory.create(
            db_session,
            name=original_name,
            bio=original_bio,
            position=original_position,
        )

        updated_name = fake.name()
        updated_user = update_user(db_session, user.id, name=updated_name)

        assert updated_user.name == updated_name
        assert updated_user.bio == original_bio
        assert updated_user.position == original_position

    def test_update_user_with_actor(self, db_session: Session):
        """Test updating user with actor_user_id for audit"""
        user = UserFactory.create(db_session)
        actor_id = uuid.uuid4()

        updated_user = update_user(
            db_session,
            user.id,
            actor_user_id=actor_id,
            name="Updated",
        )

        assert updated_user.name == "Updated"

    def test_update_user_empty_updates(self, db_session: Session):
        """Test updating user with no changes"""
        original_name = fake.name()
        user = UserFactory.create(db_session, name=original_name)

        updated_user = update_user(db_session, user.id)

        assert updated_user.name == original_name
        assert updated_user.id == user.id


class TestDeleteUser:
    """Tests for delete_user function"""

    def test_delete_user_success(self, db_session: Session):
        """Test deleting a user"""
        user = UserFactory.create(db_session)
        user_id = user.id

        result = delete_user(db_session, user_id)

        assert result is True
        # Verify user is deleted
        deleted_user = db_session.query(User).filter(User.id == user_id).first()
        assert deleted_user is None

    def test_delete_user_not_found(self, db_session: Session):
        """Test deleting non-existent user raises error"""
        fake_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            delete_user(db_session, fake_id)

        assert exc_info.value.status_code == 404

    def test_delete_user_with_actor(self, db_session: Session):
        """Test deleting user with actor_user_id for audit"""
        user = UserFactory.create(db_session)
        actor_id = uuid.uuid4()

        result = delete_user(db_session, user.id, actor_user_id=actor_id)

        assert result is True

    def test_delete_user_cascade_cleanup(self, db_session: Session):
        """Test that deleting user cleans up related data"""
        from app.models.project import UserProject
        from tests.factories import ProjectFactory, UserProjectFactory

        user = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=user)
        UserProjectFactory.create(db_session, user=user, project=project)

        # Verify relationships exist
        user_projects = db_session.query(UserProject).filter(UserProject.user_id == user.id).all()
        assert len(user_projects) > 0

        # Delete user
        delete_user(db_session, user.id)

        # Verify user is deleted
        deleted_user = db_session.query(User).filter(User.id == user.id).first()
        assert deleted_user is None


class TestGetUsers:
    """Tests for get_users function"""

    def test_get_users_all(self, db_session: Session):
        """Test getting all users"""
        UserFactory.create_batch(db_session, count=3)

        users, total = get_users(db_session)

        assert len(users) > 0
        assert total >= 3

    def test_get_users_with_pagination(self, db_session: Session):
        """Test getting users with pagination"""
        UserFactory.create_batch(db_session, count=5)

        users, total = get_users(db_session, page=1, limit=2)

        assert len(users) <= 2
        assert total >= 5

    def test_get_users_filter_by_email(self, db_session: Session):
        """Test filtering users by email"""
        filter_email = fake.email()
        user = UserFactory.create(db_session, email=filter_email)

        users, total = get_users(db_session, email=filter_email)

        assert len(users) == 1
        assert users[0].id == user.id

    def test_get_users_filter_by_name(self, db_session: Session):
        """Test filtering users by name"""
        search_name = fake.name()
        user = UserFactory.create(db_session, name=search_name)

        users, total = get_users(db_session, name=search_name.split()[0])  # Search by first name

        assert len(users) >= 1
        assert any(u.id == user.id for u in users)

    def test_get_users_filter_by_position(self, db_session: Session):
        """Test filtering users by position"""
        search_position = fake.job()
        user = UserFactory.create(db_session, position=search_position)

        users, total = get_users(db_session, position=search_position)

        assert len(users) >= 1
        assert any(u.id == user.id for u in users)

    def test_get_users_sorting_ascending(self, db_session: Session):
        """Test sorting users in ascending order"""
        UserFactory.create_batch(db_session, count=3)

        users, total = get_users(db_session, order_by="created_at", dir="asc")

        assert len(users) > 0
        # Verify ascending order
        for i in range(len(users) - 1):
            assert users[i].created_at <= users[i + 1].created_at

    def test_get_users_sorting_descending(self, db_session: Session):
        """Test sorting users in descending order"""
        UserFactory.create_batch(db_session, count=3)

        users, total = get_users(db_session, order_by="created_at", dir="desc")

        assert len(users) > 0
        # Verify descending order
        for i in range(len(users) - 1):
            assert users[i].created_at >= users[i + 1].created_at

    def test_get_users_default_pagination(self, db_session: Session):
        """Test default pagination values"""
        UserFactory.create_batch(db_session, count=25)

        users, total = get_users(db_session)

        assert len(users) <= 20  # Default limit is 20


class TestCheckEmailExists:
    """Tests for check_email_exists function"""

    def test_check_email_exists_true(self, db_session: Session):
        """Test checking if existing email exists"""
        exists_email = fake.email()
        user = UserFactory.create(db_session, email=exists_email)

        exists = check_email_exists(db_session, exists_email)

        assert exists is True

    def test_check_email_exists_false(self, db_session: Session):
        """Test checking if non-existent email exists"""
        # Generate a unique email that definitely doesn't exist
        non_existent_email = f"nonexistent_{uuid.uuid4()}@testdomain.com"
        exists = check_email_exists(db_session, non_existent_email)

        assert exists is False

    def test_check_email_exists_case_sensitive(self, db_session: Session):
        """Test that email check is case-sensitive"""
        case_email = fake.email()
        UserFactory.create(db_session, email=case_email)

        # Different case should not match
        exists = check_email_exists(db_session, case_email.upper())

        assert exists is False


class TestBulkCreateUsers:
    """Tests for bulk_create_users function"""

    def test_bulk_create_users_success(self, db_session: Session):
        """Test bulk creating multiple users"""
        # Generate unique emails to avoid conflicts
        users_data = [
            {"email": f"bulk_user1_{uuid.uuid4()}@testdomain.com", "name": fake.name()},
            {"email": f"bulk_user2_{uuid.uuid4()}@testdomain.com", "name": fake.name()},
            {"email": f"bulk_user3_{uuid.uuid4()}@testdomain.com", "name": fake.name()},
        ]

        results = bulk_create_users(db_session, users_data)

        assert len(results) == 3
        assert all(r["success"] for r in results)
        assert all(r["id"] is not None for r in results)

    def test_bulk_create_users_with_duplicate(self, db_session: Session):
        """Test bulk creating users with duplicate email"""
        duplicate_email = fake.email()
        users_data = [
            {"email": duplicate_email, "name": fake.name()},
            {"email": duplicate_email, "name": fake.name()},
        ]

        results = bulk_create_users(db_session, users_data)

        # First should succeed
        assert results[0]["success"] is True
        # Second should fail due to duplicate email
        assert results[1]["success"] is False
        # Error should mention email already exists
        error_msg = results[1]["error"].lower()
        assert "already exists" in error_msg

    def test_bulk_create_users_empty_list(self, db_session: Session):
        """Test bulk creating with empty list"""
        results = bulk_create_users(db_session, [])

        assert results == []

    def test_bulk_create_users_partial_data(self, db_session: Session):
        """Test bulk creating users with partial data"""
        users_data = [
            {"email": fake.email()},
            {"email": fake.email(), "name": fake.name()},
        ]

        results = bulk_create_users(db_session, users_data)

        assert len(results) == 2
        # Both should succeed since partial data is allowed (only email is required)
        assert results[0]["success"] is True
        assert results[1]["success"] is True
        assert results[0]["id"] is not None
        assert results[1]["id"] is not None


class TestBulkUpdateUsers:
    """Tests for bulk_update_users function"""

    def test_bulk_update_users_success(self, db_session: Session):
        """Test bulk updating multiple users"""
        user1_name = fake.name()
        user2_name = fake.name()
        user1 = UserFactory.create(db_session, name=user1_name)
        user2 = UserFactory.create(db_session, name=user2_name)

        updated_name1 = fake.name()
        updated_name2 = fake.name()
        updates = [
            {"id": user1.id, "updates": {"name": updated_name1}},
            {"id": user2.id, "updates": {"name": updated_name2}},
        ]

        results = bulk_update_users(db_session, updates)

        assert len(results) == 2
        assert all(r["success"] for r in results)

        # Verify updates
        updated_user1 = db_session.query(User).filter(User.id == user1.id).first()
        assert updated_user1.name == updated_name1

    def test_bulk_update_users_not_found(self, db_session: Session):
        """Test bulk updating with non-existent user"""
        fake_id = uuid.uuid4()

        updates = [
            {"id": fake_id, "updates": {"name": "Updated"}},
        ]

        results = bulk_update_users(db_session, updates)

        assert results[0]["success"] is False
        assert MessageDescriptions.USER_NOT_FOUND.lower() in results[0]["error"].lower()

    def test_bulk_update_users_mixed_success(self, db_session: Session):
        """Test bulk updating with mix of valid and invalid users"""
        user1_name = fake.name()
        user1 = UserFactory.create(db_session, name=user1_name)
        fake_id = uuid.uuid4()

        updated_name = fake.name()
        updates = [
            {"id": user1.id, "updates": {"name": updated_name}},
            {"id": fake_id, "updates": {"name": fake.name()}},
        ]

        results = bulk_update_users(db_session, updates)

        assert results[0]["success"] is True
        assert results[1]["success"] is False

    def test_bulk_update_users_empty_list(self, db_session: Session):
        """Test bulk updating with empty list"""
        results = bulk_update_users(db_session, [])

        assert results == []


class TestBulkDeleteUsers:
    """Tests for bulk_delete_users function"""

    def test_bulk_delete_users_success(self, db_session: Session):
        """Test bulk deleting multiple users"""
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)

        results = bulk_delete_users(db_session, [user1.id, user2.id])

        assert len(results) == 2
        assert all(r["success"] for r in results)

        # Verify deletion
        deleted_user1 = db_session.query(User).filter(User.id == user1.id).first()
        assert deleted_user1 is None

    def test_bulk_delete_users_not_found(self, db_session: Session):
        """Test bulk deleting with non-existent user"""
        fake_id = uuid.uuid4()

        results = bulk_delete_users(db_session, [fake_id])

        assert results[0]["success"] is False
        assert MessageDescriptions.USER_NOT_FOUND.lower() in results[0]["error"].lower()

    def test_bulk_delete_users_mixed_success(self, db_session: Session):
        """Test bulk deleting with mix of valid and invalid users"""
        user1 = UserFactory.create(db_session)
        fake_id = uuid.uuid4()

        results = bulk_delete_users(db_session, [user1.id, fake_id])

        assert results[0]["success"] is True
        assert results[1]["success"] is False

    def test_bulk_delete_users_empty_list(self, db_session: Session):
        """Test bulk deleting with empty list"""
        results = bulk_delete_users(db_session, [])

        assert results == []


class TestGetUserById:
    """Tests for get_user_by_id function"""

    def test_get_user_by_id_success(self, db_session: Session):
        """Test getting user by ID"""
        user = UserFactory.create(db_session)

        retrieved_user = get_user_by_id(db_session, user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.email == user.email

    def test_get_user_by_id_not_found(self, db_session: Session):
        """Test getting non-existent user by ID"""
        fake_id = uuid.uuid4()

        user = get_user_by_id(db_session, fake_id)

        assert user is None
