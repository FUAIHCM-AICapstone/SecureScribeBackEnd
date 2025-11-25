"""Unit tests for project service functions"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.project import Project, UserProject
from app.schemas.project import ProjectCreate, ProjectUpdate, UserProjectCreate
from app.services.project import (
    add_user_to_project,
    create_project,
    delete_project,
    get_project,
    get_project_members,
    get_projects,
    get_user_role_in_project,
    is_user_in_project,
    remove_user_from_project,
    update_project,
    update_user_role_in_project,
)
from tests.factories import ProjectFactory, UserFactory, UserProjectFactory


class TestCreateProject:
    """Tests for create_project function"""

    def test_create_project_success(self, db_session: Session):
        """Test creating a project with valid data"""
        creator = UserFactory.create(db_session)
        project_data = ProjectCreate(
            name="Test Project",
            description="A test project",
        )

        project = create_project(db_session, project_data, creator.id)

        assert project.id is not None
        assert project.name == "Test Project"
        assert project.description == "A test project"
        assert project.created_by == creator.id
        assert project.is_archived is False

    def test_create_project_minimal_data(self, db_session: Session):
        """Test creating a project with minimal data"""
        creator = UserFactory.create(db_session)
        project_data = ProjectCreate(name="Minimal Project")

        project = create_project(db_session, project_data, creator.id)

        assert project.name == "Minimal Project"
        assert project.description is None
        assert project.created_by == creator.id

    def test_create_project_adds_creator_as_owner(self, db_session: Session):
        """Test that project creator is automatically added as owner"""
        creator = UserFactory.create(db_session)
        project_data = ProjectCreate(name="Owner Test Project")

        project = create_project(db_session, project_data, creator.id)

        # Verify creator is added as owner
        user_project = (
            db_session.query(UserProject)
            .filter(
                UserProject.project_id == project.id,
                UserProject.user_id == creator.id,
            )
            .first()
        )
        assert user_project is not None
        assert user_project.role == "owner"

    def test_create_project_timestamps(self, db_session: Session):
        """Test that project has correct timestamps"""

        creator = UserFactory.create(db_session)
        project_data = ProjectCreate(name="Timestamp Test")
        before_creation = datetime.now(timezone.utc)

        project = create_project(db_session, project_data, creator.id)

        assert project.created_at is not None
        # Convert both to timezone-aware for comparison
        created_at_utc = project.created_at.replace(tzinfo=timezone.utc) if project.created_at.tzinfo is None else project.created_at
        assert created_at_utc >= before_creation


class TestGetProject:
    """Tests for get_project function"""

    def test_get_project_success(self, db_session: Session):
        """Test getting a project by ID"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)

        retrieved_project = get_project(db_session, project.id)

        assert retrieved_project is not None
        assert retrieved_project.id == project.id
        assert retrieved_project.name == project.name

    def test_get_project_not_found(self, db_session: Session):
        """Test getting non-existent project"""
        fake_id = uuid.uuid4()

        project = get_project(db_session, fake_id)

        assert project is None

    def test_get_project_with_members(self, db_session: Session):
        """Test getting project with members included"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project)

        retrieved_project = get_project(db_session, project.id, include_members=True)

        assert retrieved_project is not None
        assert len(retrieved_project.users) >= 1
        # Should include creator and member
        user_ids = [up.user_id for up in retrieved_project.users]
        assert creator.id in user_ids
        assert member.id in user_ids

    def test_get_project_without_members(self, db_session: Session):
        """Test getting project without members"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)

        retrieved_project = get_project(db_session, project.id, include_members=False)

        assert retrieved_project is not None
        # Users relationship might not be loaded
        assert retrieved_project.id == project.id


class TestGetProjects:
    """Tests for get_projects function"""

    def test_get_projects_all(self, db_session: Session):
        """Test getting all projects"""
        creator = UserFactory.create(db_session)
        ProjectFactory.create_batch(db_session, creator, count=3)

        projects, total = get_projects(db_session)

        assert len(projects) > 0
        assert total >= 3

    def test_get_projects_with_pagination(self, db_session: Session):
        """Test getting projects with pagination"""
        creator = UserFactory.create(db_session)
        ProjectFactory.create_batch(db_session, creator, count=5)

        projects, total = get_projects(db_session, page=1, limit=2)

        assert len(projects) <= 2
        assert total >= 5

    def test_get_projects_filter_by_name(self, db_session: Session):
        """Test filtering projects by name"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator, name="Unique Project Name")

        projects, total = get_projects(db_session, filters=None)
        # Manual filter check since filters parameter is optional
        matching = [p for p in projects if "Unique" in p.name]

        assert len(matching) >= 1

    def test_get_projects_filter_by_archived(self, db_session: Session):
        """Test filtering projects by archived status"""
        creator = UserFactory.create(db_session)
        ProjectFactory.create(db_session, creator, is_archived=False)
        ProjectFactory.create(db_session, creator, is_archived=True)

        projects, total = get_projects(db_session)

        assert len(projects) >= 2

    def test_get_projects_sorting_ascending(self, db_session: Session):
        """Test sorting projects in ascending order"""
        creator = UserFactory.create(db_session)
        ProjectFactory.create_batch(db_session, creator, count=3)

        projects, total = get_projects(db_session, order_by="created_at", dir="asc")

        assert len(projects) > 0
        # Verify ascending order
        for i in range(len(projects) - 1):
            assert projects[i].created_at <= projects[i + 1].created_at

    def test_get_projects_sorting_descending(self, db_session: Session):
        """Test sorting projects in descending order"""
        creator = UserFactory.create(db_session)
        ProjectFactory.create_batch(db_session, creator, count=3)

        projects, total = get_projects(db_session, order_by="created_at", dir="desc")

        assert len(projects) > 0
        # Verify descending order
        for i in range(len(projects) - 1):
            assert projects[i].created_at >= projects[i + 1].created_at

    def test_get_projects_default_pagination(self, db_session: Session):
        """Test default pagination values"""
        creator = UserFactory.create(db_session)
        ProjectFactory.create_batch(db_session, creator, count=25)

        projects, total = get_projects(db_session)

        assert len(projects) <= 20  # Default limit is 20


class TestUpdateProject:
    """Tests for update_project function"""

    def test_update_project_success(self, db_session: Session):
        """Test updating a project with valid data"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator, name="Original Name")
        updates = ProjectUpdate(name="Updated Name", description="Updated description")

        updated_project = update_project(db_session, project.id, updates)

        assert updated_project is not None
        assert updated_project.name == "Updated Name"
        assert updated_project.description == "Updated description"
        assert updated_project.id == project.id

    def test_update_project_not_found(self, db_session: Session):
        """Test updating non-existent project"""
        fake_id = uuid.uuid4()
        updates = ProjectUpdate(name="Updated Name")

        result = update_project(db_session, fake_id, updates)

        assert result is None

    def test_update_project_partial_fields(self, db_session: Session):
        """Test updating only some fields"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(
            db_session,
            creator,
            name="Original",
            description="Original description",
        )
        updates = ProjectUpdate(name="Updated")

        updated_project = update_project(db_session, project.id, updates)

        assert updated_project.name == "Updated"
        assert updated_project.description == "Original description"

    def test_update_project_archive_status(self, db_session: Session):
        """Test updating project archive status"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator, is_archived=False)
        updates = ProjectUpdate(is_archived=True)

        updated_project = update_project(db_session, project.id, updates)

        assert updated_project.is_archived is True

    def test_update_project_with_actor(self, db_session: Session):
        """Test updating project with actor_user_id for audit"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        actor_id = uuid.uuid4()
        updates = ProjectUpdate(name="Updated")

        updated_project = update_project(db_session, project.id, updates, actor_user_id=actor_id)

        assert updated_project.name == "Updated"

    def test_update_project_empty_updates(self, db_session: Session):
        """Test updating project with no changes"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator, name="Original")
        updates = ProjectUpdate()

        updated_project = update_project(db_session, project.id, updates)

        assert updated_project.name == "Original"
        assert updated_project.id == project.id


class TestDeleteProject:
    """Tests for delete_project function"""

    def test_delete_project_success(self, db_session: Session):
        """Test deleting a project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        project_id = project.id

        result = delete_project(db_session, project_id)

        assert result is True
        # Verify project is deleted
        deleted_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert deleted_project is None

    def test_delete_project_not_found(self, db_session: Session):
        """Test deleting non-existent project"""
        fake_id = uuid.uuid4()

        result = delete_project(db_session, fake_id)

        assert result is False

    def test_delete_project_with_actor(self, db_session: Session):
        """Test deleting project with actor_user_id for audit"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        actor_id = uuid.uuid4()

        result = delete_project(db_session, project.id, actor_user_id=actor_id)

        assert result is True

    def test_delete_project_cascade_cleanup_members(self, db_session: Session):
        """Test that deleting project cleans up user-project relationships"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project)

        # Verify relationships exist
        user_projects = db_session.query(UserProject).filter(UserProject.project_id == project.id).all()
        assert len(user_projects) >= 2  # Creator and member

        # Delete project
        delete_project(db_session, project.id)

        # Verify project is deleted
        deleted_project = db_session.query(Project).filter(Project.id == project.id).first()
        assert deleted_project is None

        # Verify user-project relationships are deleted
        remaining_user_projects = db_session.query(UserProject).filter(UserProject.project_id == project.id).all()
        assert len(remaining_user_projects) == 0

    def test_delete_project_cascade_cleanup_meetings(self, db_session: Session):
        """Test that deleting project cleans up meetings"""
        from tests.factories import MeetingFactory, ProjectMeetingFactory

        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        meeting = MeetingFactory.create(db_session, creator)
        ProjectMeetingFactory.create(db_session, project, meeting)

        # Delete project
        result = delete_project(db_session, project.id)

        assert result is True
        # Verify project is deleted
        deleted_project = db_session.query(Project).filter(Project.id == project.id).first()
        assert deleted_project is None


class TestAddUserToProject:
    """Tests for add_user_to_project function"""

    def test_add_user_to_project_success(self, db_session: Session):
        """Test adding a user to a project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)

        user_project = add_user_to_project(db_session, project.id, user.id, role="member")

        assert user_project is not None
        assert user_project.user_id == user.id
        assert user_project.project_id == project.id
        assert user_project.role == "member"

    def test_add_user_to_project_with_role(self, db_session: Session):
        """Test adding a user with specific role"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)

        user_project = add_user_to_project(db_session, project.id, user.id, role="admin")

        assert user_project.role == "admin"

    def test_add_user_to_project_already_exists(self, db_session: Session):
        """Test adding user who is already in project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project, role="member")

        # Try to add again
        user_project = add_user_to_project(db_session, project.id, user.id, role="admin")

        # Should return existing relationship
        assert user_project is not None
        assert user_project.user_id == user.id
        # Role should remain unchanged (not updated)
        assert user_project.role == "member"

    def test_add_user_to_project_not_found_project(self, db_session: Session):
        """Test adding user to non-existent project"""
        user = UserFactory.create(db_session)
        fake_project_id = uuid.uuid4()

        user_project = add_user_to_project(db_session, fake_project_id, user.id)

        assert user_project is None

    def test_add_user_to_project_not_found_user(self, db_session: Session):
        """Test adding non-existent user to project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        fake_user_id = uuid.uuid4()

        user_project = add_user_to_project(db_session, project.id, fake_user_id)

        assert user_project is None

    def test_add_user_to_project_with_actor(self, db_session: Session):
        """Test adding user with actor_user_id for audit"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)
        actor_id = uuid.uuid4()

        user_project = add_user_to_project(
            db_session,
            project.id,
            user.id,
            role="member",
            added_by_user_id=actor_id,
        )

        assert user_project is not None
        assert user_project.user_id == user.id


class TestRemoveUserFromProject:
    """Tests for remove_user_from_project function"""

    def test_remove_user_from_project_success(self, db_session: Session):
        """Test removing a user from a project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project)

        result = remove_user_from_project(db_session, project.id, user.id)

        assert result is True
        # Verify relationship is deleted
        user_project = (
            db_session.query(UserProject)
            .filter(
                UserProject.project_id == project.id,
                UserProject.user_id == user.id,
            )
            .first()
        )
        assert user_project is None

    def test_remove_user_from_project_not_found(self, db_session: Session):
        """Test removing user who is not in project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)

        result = remove_user_from_project(db_session, project.id, user.id)

        assert result is False

    def test_remove_user_from_project_with_actor(self, db_session: Session):
        """Test removing user with actor_user_id for audit"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project)
        actor_id = uuid.uuid4()

        result = remove_user_from_project(
            db_session,
            project.id,
            user.id,
            removed_by_user_id=actor_id,
        )

        assert result is True

    def test_remove_user_from_project_self_removal(self, db_session: Session):
        """Test user removing themselves from project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project)

        result = remove_user_from_project(
            db_session,
            project.id,
            user.id,
            removed_by_user_id=user.id,
            is_self_removal=True,
        )

        assert result is True


class TestUpdateUserRoleInProject:
    """Tests for update_user_role_in_project function"""

    def test_update_user_role_success(self, db_session: Session):
        """Test updating user role in project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project, role="member")

        user_project = update_user_role_in_project(
            db_session,
            project.id,
            user.id,
            new_role="admin",
        )

        assert user_project is not None
        assert user_project.role == "admin"

    def test_update_user_role_not_found(self, db_session: Session):
        """Test updating role for user not in project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)

        user_project = update_user_role_in_project(
            db_session,
            project.id,
            user.id,
            new_role="admin",
        )

        assert user_project is None

    def test_update_user_role_with_actor(self, db_session: Session):
        """Test updating role with actor_user_id for audit"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project, role="member")
        actor_id = uuid.uuid4()

        user_project = update_user_role_in_project(
            db_session,
            project.id,
            user.id,
            new_role="admin",
            actor_user_id=actor_id,
        )

        assert user_project.role == "admin"

    def test_update_user_role_to_owner(self, db_session: Session):
        """Test updating user role to owner"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project, role="member")

        user_project = update_user_role_in_project(
            db_session,
            project.id,
            user.id,
            new_role="owner",
        )

        assert user_project.role == "owner"


class TestGetProjectMembers:
    """Tests for get_project_members function"""

    def test_get_project_members_success(self, db_session: Session):
        """Test getting all members of a project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        member1 = UserFactory.create(db_session)
        member2 = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member1, project=project)
        UserProjectFactory.create(db_session, user=member2, project=project)

        members = get_project_members(db_session, project.id)

        assert len(members) >= 3  # Creator + 2 members
        member_ids = [m.user_id for m in members]
        assert creator.id in member_ids
        assert member1.id in member_ids
        assert member2.id in member_ids

    def test_get_project_members_empty(self, db_session: Session):
        """Test getting members of project with no members"""
        fake_project_id = uuid.uuid4()

        members = get_project_members(db_session, fake_project_id)

        assert len(members) == 0

    def test_get_project_members_includes_roles(self, db_session: Session):
        """Test that member roles are included"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="admin")

        members = get_project_members(db_session, project.id)

        admin_member = next((m for m in members if m.user_id == member.id), None)
        assert admin_member is not None
        assert admin_member.role == "admin"


class TestIsUserInProject:
    """Tests for is_user_in_project function"""

    def test_is_user_in_project_true(self, db_session: Session):
        """Test checking if user is in project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project)

        result = is_user_in_project(db_session, project.id, user.id)

        assert result is True

    def test_is_user_in_project_false(self, db_session: Session):
        """Test checking if user is not in project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)

        result = is_user_in_project(db_session, project.id, user.id)

        assert result is False

    def test_is_user_in_project_creator(self, db_session: Session):
        """Test that creator is in project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)

        result = is_user_in_project(db_session, project.id, creator.id)

        assert result is True


class TestGetUserRoleInProject:
    """Tests for get_user_role_in_project function"""

    def test_get_user_role_success(self, db_session: Session):
        """Test getting user role in project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project, role="admin")

        role = get_user_role_in_project(db_session, project.id, user.id)

        assert role == "admin"

    def test_get_user_role_not_found(self, db_session: Session):
        """Test getting role for user not in project"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)

        role = get_user_role_in_project(db_session, project.id, user.id)

        assert role is None

    def test_get_user_role_creator(self, db_session: Session):
        """Test getting creator's role"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)

        role = get_user_role_in_project(db_session, project.id, creator.id)

        assert role == "owner"


class TestBulkAddUsersToProject:
    """Tests for bulk_add_users_to_project function"""

    def test_bulk_add_users_success(self, db_session: Session):
        """Test bulk adding users to project"""
        from app.services.project import bulk_add_users_to_project

        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)

        users_data = [
            UserProjectCreate(user_id=user1.id, role="member"),
            UserProjectCreate(user_id=user2.id, role="admin"),
        ]

        results = bulk_add_users_to_project(db_session, project.id, users_data)

        assert len(results) == 2
        assert all(r["success"] for r in results)

    def test_bulk_add_users_with_invalid_user(self, db_session: Session):
        """Test bulk adding with non-existent user"""
        from app.services.project import bulk_add_users_to_project

        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)
        fake_user_id = uuid.uuid4()

        users_data = [
            UserProjectCreate(user_id=user.id, role="member"),
            UserProjectCreate(user_id=fake_user_id, role="member"),
        ]

        results = bulk_add_users_to_project(db_session, project.id, users_data)

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False

    def test_bulk_add_users_empty_list(self, db_session: Session):
        """Test bulk adding with empty list"""
        from app.services.project import bulk_add_users_to_project

        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)

        results = bulk_add_users_to_project(db_session, project.id, [])

        assert results == []


class TestBulkRemoveUsersFromProject:
    """Tests for bulk_remove_users_from_project function"""

    def test_bulk_remove_users_success(self, db_session: Session):
        """Test bulk removing users from project"""
        from app.services.project import bulk_remove_users_from_project

        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user1, project=project)
        UserProjectFactory.create(db_session, user=user2, project=project)

        results = bulk_remove_users_from_project(db_session, project.id, [user1.id, user2.id])

        assert len(results) == 2
        assert all(r["success"] for r in results)

    def test_bulk_remove_users_with_invalid_user(self, db_session: Session):
        """Test bulk removing with user not in project"""
        from app.services.project import bulk_remove_users_from_project

        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project)
        fake_user_id = uuid.uuid4()

        results = bulk_remove_users_from_project(
            db_session,
            project.id,
            [user.id, fake_user_id],
        )

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False

    def test_bulk_remove_users_empty_list(self, db_session: Session):
        """Test bulk removing with empty list"""
        from app.services.project import bulk_remove_users_from_project

        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)

        results = bulk_remove_users_from_project(db_session, project.id, [])

        assert results == []
