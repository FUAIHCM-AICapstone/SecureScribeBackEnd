"""API endpoint tests for project management"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models.project import Project, UserProject
from tests.factories import ProjectFactory, UserFactory, UserProjectFactory


class TestGetProjectsEndpoint:
    """Tests for GET /projects endpoint"""

    def test_get_projects_returns_paginated_list(self, client: TestClient, db_session: Session, test_user):
        """Test that GET /projects returns paginated list of projects"""
        # Arrange: Create test projects with authenticated user
        projects = ProjectFactory.create_batch(db_session, test_user, count=5)

        # Act: Get projects
        response = client.get("/api/v1/projects?page=1&limit=10")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 5
        assert data["pagination"]["total"] >= 5

    def test_get_projects_with_pagination(self, client: TestClient, db_session: Session, test_user):
        """Test that pagination works correctly"""
        # Arrange: Create 15 test projects with authenticated user
        ProjectFactory.create_batch(db_session, test_user, count=15)

        # Act: Get first page with limit 5
        response = client.get("/api/v1/projects?page=1&limit=5")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 5

    def test_get_projects_with_name_filter(self, client: TestClient, db_session: Session, test_user):
        """Test that name filter works correctly"""
        # Arrange: Create projects with specific names using authenticated user
        project1 = ProjectFactory.create(db_session, test_user, name="Alpha Project")
        project2 = ProjectFactory.create(db_session, test_user, name="Beta Project")
        ProjectFactory.create(db_session, test_user, name="Gamma Project")

        # Act: Filter by name
        response = client.get("/api/v1/projects?name=Alpha")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        names = [p["name"] for p in data["data"]]
        assert any("Alpha" in name for name in names)

    def test_get_projects_with_archived_filter(self, client: TestClient, db_session: Session, test_user):
        """Test that archived filter works correctly"""
        # Arrange: Create archived and non-archived projects with authenticated user
        ProjectFactory.create(db_session, test_user, is_archived=False)
        ProjectFactory.create(db_session, test_user, is_archived=True)

        # Act: Filter by archived status
        response = client.get("/api/v1/projects?is_archived=false")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1

    def test_get_projects_with_ordering(self, client: TestClient, db_session: Session, test_user):
        """Test that ordering works correctly"""
        # Arrange: Create test projects with authenticated user
        ProjectFactory.create_batch(db_session, test_user, count=3)

        # Act: Get projects ordered by created_at descending
        response = client.get("/api/v1/projects?order_by=created_at&dir=desc")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 3

    def test_get_projects_empty_result(self, client: TestClient, db_session: Session):
        """Test that empty filter returns empty list"""
        # Act: Filter by non-existent name
        response = client.get("/api/v1/projects?name=NonexistentProjectName12345")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) == 0


class TestCreateProjectEndpoint:
    """Tests for POST /projects endpoint"""

    def test_create_project_with_valid_data(self, client: TestClient, db_session: Session):
        """Test creating a project with valid data"""
        # Arrange
        project_data = {
            "name": "New Project",
            "description": "A new test project",
        }

        # Act
        response = client.post("/api/v1/projects", json=project_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "New Project"
        assert data["data"]["description"] == "A new test project"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            project_id = uuid.UUID(data["data"]["id"])
            db_project = fresh_session.query(Project).filter(Project.id == project_id).first()
            assert db_project is not None
            assert db_project.name == "New Project"
        finally:
            fresh_session.close()

    def test_create_project_with_minimal_data(self, client: TestClient, db_session: Session):
        """Test creating a project with only required name"""
        # Arrange
        project_data = {"name": "Minimal Project"}

        # Act
        response = client.post("/api/v1/projects", json=project_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Minimal Project"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            project_id = uuid.UUID(data["data"]["id"])
            db_project = fresh_session.query(Project).filter(Project.id == project_id).first()
            assert db_project is not None
        finally:
            fresh_session.close()

    def test_create_project_adds_creator_as_owner(self, client: TestClient, db_session: Session):
        """Test that project creator is automatically added as owner"""
        # Arrange
        project_data = {"name": "Owner Test Project"}

        # Act
        response = client.post("/api/v1/projects", json=project_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        project_id = uuid.UUID(data["data"]["id"])

        # Verify creator is added as owner
        fresh_session = SessionLocal()
        try:
            user_project = fresh_session.query(UserProject).filter(UserProject.project_id == project_id).first()
            assert user_project is not None
            assert user_project.role == "owner"
        finally:
            fresh_session.close()

    def test_create_project_persists_to_database(self, client: TestClient, db_session: Session):
        """Test that created project is persisted to database"""
        # Arrange
        project_data = {
            "name": "Persist Project",
            "description": "Test persistence",
        }

        # Act
        response = client.post("/api/v1/projects", json=project_data)

        # Assert
        assert response.status_code == 200
        project_id = uuid.UUID(response.json()["data"]["id"])

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_project = fresh_session.query(Project).filter(Project.id == project_id).first()
            assert db_project is not None
            assert db_project.name == "Persist Project"
            assert db_project.description == "Test persistence"
        finally:
            fresh_session.close()


class TestGetProjectEndpoint:
    """Tests for GET /projects/{id} endpoint"""

    def test_get_project_success(self, client: TestClient, db_session: Session, test_user):
        """Test getting a project by ID"""
        # Arrange: Create project with authenticated user
        project = ProjectFactory.create(db_session, test_user)

        # Act: Get project
        response = client.get(f"/api/v1/projects/{project.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == str(project.id)
        assert data["data"]["name"] == project.name

    def test_get_project_not_found(self, client: TestClient, db_session: Session):
        """Test getting non-existent project"""
        # Arrange
        fake_id = uuid.uuid4()

        # Act
        response = client.get(f"/api/v1/projects/{fake_id}")

        # Assert
        assert response.status_code == 404

    def test_get_project_with_members(self, client: TestClient, db_session: Session, test_user):
        """Test getting project with members included"""
        # Arrange: Create project with members using authenticated user
        project = ProjectFactory.create(db_session, test_user)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project)

        # Act: Get project with members
        response = client.get(f"/api/v1/projects/{project.id}?include_members=true")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "members" in data["data"]
        assert len(data["data"]["members"]) >= 2  # Creator and member

    def test_get_project_access_denied_for_non_member(self, client: TestClient, db_session: Session):
        """Test that non-members cannot access project"""
        # Arrange: Create project with different creator
        other_creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, other_creator)

        # Act: Try to get project as different user
        response = client.get(f"/api/v1/projects/{project.id}")

        # Assert
        assert response.status_code == 403


class TestUpdateProjectEndpoint:
    """Tests for PUT /projects/{id} endpoint"""

    def test_update_project_with_valid_data(self, client: TestClient, db_session: Session, test_user):
        """Test updating a project with valid data"""
        # Arrange: Create project with authenticated user
        project = ProjectFactory.create(db_session, test_user, name="Original Name")

        # Act: Update project
        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
        }
        response = client.put(f"/api/v1/projects/{project.id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Updated Name"
        assert data["data"]["description"] == "Updated description"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_project = fresh_session.query(Project).filter(Project.id == project.id).first()
            assert db_project.name == "Updated Name"
            assert db_project.description == "Updated description"
        finally:
            fresh_session.close()

    def test_update_project_partial_fields(self, client: TestClient, db_session: Session, test_user):
        """Test updating only some fields"""
        # Arrange: Create project with authenticated user
        project = ProjectFactory.create(
            db_session,
            test_user,
            name="Original",
            description="Original description",
        )

        # Act: Update only name
        update_data = {"name": "Updated"}
        response = client.put(f"/api/v1/projects/{project.id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Updated"

        # Verify description unchanged
        db_project = db_session.query(Project).filter(Project.id == project.id).first()
        assert db_project.description == "Original description"

    def test_update_project_archive_status(self, client: TestClient, db_session: Session, test_user):
        """Test updating project archive status"""
        # Arrange: Create project with authenticated user
        project = ProjectFactory.create(db_session, test_user, is_archived=False)

        # Act: Archive project
        update_data = {"is_archived": True}
        response = client.put(f"/api/v1/projects/{project.id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_archived"] is True

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_project = fresh_session.query(Project).filter(Project.id == project.id).first()
            assert db_project.is_archived is True
        finally:
            fresh_session.close()

    def test_update_project_nonexistent(self, client: TestClient, db_session: Session):
        """Test updating non-existent project returns 403 (access denied)"""
        # Arrange
        fake_id = uuid.uuid4()

        # Act: Try to update a project that doesn't exist
        response = client.put(f"/api/v1/projects/{fake_id}", json={"name": "Updated"})

        # Assert: Should get 403 because user is not admin of non-existent project
        assert response.status_code == 403

    def test_update_project_requires_admin_access(self, client: TestClient, db_session: Session):
        """Test that only admins can update project"""
        # Arrange: Create project with different creator
        other_creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, other_creator)

        # Act: Try to update as non-admin
        response = client.put(f"/api/v1/projects/{project.id}", json={"name": "Updated"})

        # Assert
        assert response.status_code == 403

    def test_update_project_persists_to_database(self, client: TestClient, db_session: Session, test_user):
        """Test that project updates persist to database"""
        # Arrange: Create project with authenticated user
        project = ProjectFactory.create(db_session, test_user, name="Original")

        # Act: Update project
        update_data = {"name": "Updated"}
        response = client.put(f"/api/v1/projects/{project.id}", json=update_data)

        # Assert
        assert response.status_code == 200

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_project = fresh_session.query(Project).filter(Project.id == project.id).first()
            assert db_project.name == "Updated"
        finally:
            fresh_session.close()


class TestDeleteProjectEndpoint:
    """Tests for DELETE /projects/{id} endpoint"""

    def test_delete_project_success(self, client: TestClient, db_session: Session, test_user):
        """Test deleting a project successfully"""
        # Arrange: Create project with authenticated user
        project = ProjectFactory.create(db_session, test_user)
        project_id = project.id

        # Act: Delete project
        response = client.delete(f"/api/v1/projects/{project_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify removed from database
        db_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert db_project is None

    def test_delete_project_nonexistent(self, client: TestClient, db_session: Session):
        """Test deleting non-existent project returns 403 (access denied)"""
        # Arrange
        fake_id = uuid.uuid4()

        # Act: Try to delete a project that doesn't exist
        response = client.delete(f"/api/v1/projects/{fake_id}")

        # Assert: Should get 403 because user is not admin of non-existent project
        assert response.status_code == 403

    def test_delete_project_requires_admin_access(self, client: TestClient, db_session: Session):
        """Test that only admins can delete project"""
        # Arrange: Create project with different creator
        other_creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, other_creator)

        # Act: Try to delete as non-admin
        response = client.delete(f"/api/v1/projects/{project.id}")

        # Assert
        assert response.status_code == 403

    def test_delete_project_removes_from_database(self, client: TestClient, db_session: Session, test_user):
        """Test that deleted project is removed from database"""
        # Arrange: Create project with authenticated user
        project = ProjectFactory.create(db_session, test_user)
        project_id = project.id

        # Verify project exists
        db_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert db_project is not None

        # Act: Delete project
        response = client.delete(f"/api/v1/projects/{project_id}")

        # Assert
        assert response.status_code == 200

        # Verify removed from database
        db_project = db_session.query(Project).filter(Project.id == project_id).first()
        assert db_project is None

    def test_delete_project_cascade_cleanup_members(self, client: TestClient, db_session: Session, test_user):
        """Test that deleting project cleans up user-project relationships"""
        # Arrange: Create project with members using authenticated user
        project = ProjectFactory.create(db_session, test_user)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project)

        # Verify relationships exist
        user_projects = db_session.query(UserProject).filter(UserProject.project_id == project.id).all()
        assert len(user_projects) >= 2  # Creator and member

        # Act: Delete project
        response = client.delete(f"/api/v1/projects/{project.id}")

        # Assert
        assert response.status_code == 200

        # Verify user-project relationships are deleted
        remaining_user_projects = db_session.query(UserProject).filter(UserProject.project_id == project.id).all()
        assert len(remaining_user_projects) == 0


class TestAddMemberToProjectEndpoint:
    """Tests for POST /projects/{id}/members endpoint"""

    def test_add_member_to_project_success(self, client: TestClient, db_session: Session, test_user):
        """Test adding a user to a project"""
        # Arrange: Create project with authenticated user and new user
        project = ProjectFactory.create(db_session, test_user)
        user = UserFactory.create(db_session)

        # Act: Add user to project
        member_data = {"user_id": str(user.id), "role": "member"}
        response = client.post(f"/api/v1/projects/{project.id}/members", json=member_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["user_id"] == str(user.id)
        assert data["data"]["role"] == "member"

        # Verify in database
        fresh_session = SessionLocal()
        try:
            user_project = (
                fresh_session.query(UserProject)
                .filter(
                    UserProject.project_id == project.id,
                    UserProject.user_id == user.id,
                )
                .first()
            )
            assert user_project is not None
            assert user_project.role == "member"
        finally:
            fresh_session.close()

    def test_add_member_with_admin_role(self, client: TestClient, db_session: Session, test_user):
        """Test adding a user with admin role"""
        # Arrange: Create project with authenticated user and new user
        project = ProjectFactory.create(db_session, test_user)
        user = UserFactory.create(db_session)

        # Act: Add user with admin role
        member_data = {"user_id": str(user.id), "role": "admin"}
        response = client.post(f"/api/v1/projects/{project.id}/members", json=member_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["role"] == "admin"

    def test_add_member_requires_admin_access(self, client: TestClient, db_session: Session):
        """Test that only admins can add members"""
        # Arrange: Create project with different creator
        other_creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, other_creator)
        user = UserFactory.create(db_session)

        # Act: Try to add member as non-admin
        member_data = {"user_id": str(user.id), "role": "member"}
        response = client.post(f"/api/v1/projects/{project.id}/members", json=member_data)

        # Assert
        assert response.status_code == 403

    def test_add_member_persists_to_database(self, client: TestClient, db_session: Session, test_user):
        """Test that added member is persisted to database"""
        # Arrange: Create project with authenticated user and new user
        project = ProjectFactory.create(db_session, test_user)
        user = UserFactory.create(db_session)

        # Act: Add user to project
        member_data = {"user_id": str(user.id), "role": "member"}
        response = client.post(f"/api/v1/projects/{project.id}/members", json=member_data)

        # Assert
        assert response.status_code == 200

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            user_project = (
                fresh_session.query(UserProject)
                .filter(
                    UserProject.project_id == project.id,
                    UserProject.user_id == user.id,
                )
                .first()
            )
            assert user_project is not None
            assert user_project.role == "member"
        finally:
            fresh_session.close()


class TestRemoveMemberFromProjectEndpoint:
    """Tests for DELETE /projects/{id}/members/{user_id} endpoint"""

    def test_remove_member_from_project_success(self, client: TestClient, db_session: Session, test_user):
        """Test removing a user from a project"""
        # Arrange: Create project with member using authenticated user
        project = ProjectFactory.create(db_session, test_user)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project)

        # Act: Remove member
        response = client.delete(f"/api/v1/projects/{project.id}/members/{member.id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify removed from database
        user_project = (
            db_session.query(UserProject)
            .filter(
                UserProject.project_id == project.id,
                UserProject.user_id == member.id,
            )
            .first()
        )
        assert user_project is None

    def test_remove_member_not_found(self, client: TestClient, db_session: Session, test_user):
        """Test removing user who is not in project"""
        # Arrange: Create project with authenticated user and new user
        project = ProjectFactory.create(db_session, test_user)
        user = UserFactory.create(db_session)

        # Act: Try to remove non-member
        response = client.delete(f"/api/v1/projects/{project.id}/members/{user.id}")

        # Assert
        assert response.status_code == 404

    def test_remove_member_requires_admin_access(self, client: TestClient, db_session: Session):
        """Test that only admins can remove members"""
        # Arrange: Create project with different creator
        other_creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, other_creator)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project)

        # Act: Try to remove member as non-admin
        response = client.delete(f"/api/v1/projects/{project.id}/members/{member.id}")

        # Assert
        assert response.status_code == 403

    def test_remove_member_persists_to_database(self, client: TestClient, db_session: Session, test_user):
        """Test that member removal is persisted to database"""
        # Arrange: Create project with member using authenticated user
        project = ProjectFactory.create(db_session, test_user)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project)

        # Act: Remove member
        response = client.delete(f"/api/v1/projects/{project.id}/members/{member.id}")

        # Assert
        assert response.status_code == 200

        # Verify removed from database with fresh session
        fresh_session = SessionLocal()
        try:
            user_project = (
                fresh_session.query(UserProject)
                .filter(
                    UserProject.project_id == project.id,
                    UserProject.user_id == member.id,
                )
                .first()
            )
            assert user_project is None
        finally:
            fresh_session.close()


class TestUpdateMemberRoleEndpoint:
    """Tests for PUT /projects/{id}/members/{user_id} endpoint"""

    def test_update_member_role_success(self, client: TestClient, db_session: Session, test_user):
        """Test updating a member's role"""
        # Arrange: Create project with member using authenticated user
        project = ProjectFactory.create(db_session, test_user)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Act: Update role to admin
        role_data = {"role": "admin"}
        response = client.put(f"/api/v1/projects/{project.id}/members/{member.id}", json=role_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["role"] == "admin"

        # Verify in database
        user_project = (
            db_session.query(UserProject)
            .filter(
                UserProject.project_id == project.id,
                UserProject.user_id == member.id,
            )
            .first()
        )
        assert user_project.role == "admin"

    def test_update_member_role_to_owner(self, client: TestClient, db_session: Session, test_user):
        """Test updating member role to owner"""
        # Arrange: Create project with member using authenticated user
        project = ProjectFactory.create(db_session, test_user)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Act: Update role to owner
        role_data = {"role": "owner"}
        response = client.put(f"/api/v1/projects/{project.id}/members/{member.id}", json=role_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["role"] == "owner"

    def test_update_member_role_not_found(self, client: TestClient, db_session: Session, test_user):
        """Test updating role for user not in project"""
        # Arrange: Create project with authenticated user and new user
        project = ProjectFactory.create(db_session, test_user)
        user = UserFactory.create(db_session)

        # Act: Try to update non-member
        role_data = {"role": "admin"}
        response = client.put(f"/api/v1/projects/{project.id}/members/{user.id}", json=role_data)

        # Assert
        assert response.status_code == 404

    def test_update_member_role_requires_admin_access(self, client: TestClient, db_session: Session):
        """Test that only admins can update member roles"""
        # Arrange: Create project with different creator
        other_creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, other_creator)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project)

        # Act: Try to update role as non-admin
        role_data = {"role": "admin"}
        response = client.put(f"/api/v1/projects/{project.id}/members/{member.id}", json=role_data)

        # Assert
        assert response.status_code == 403

    def test_update_member_role_persists_to_database(self, client: TestClient, db_session: Session, test_user):
        """Test that role updates persist to database"""
        # Arrange: Create project with member using authenticated user
        project = ProjectFactory.create(db_session, test_user)
        member = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=member, project=project, role="member")

        # Act: Update role
        role_data = {"role": "admin"}
        response = client.put(f"/api/v1/projects/{project.id}/members/{member.id}", json=role_data)

        # Assert
        assert response.status_code == 200

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            user_project = (
                fresh_session.query(UserProject)
                .filter(
                    UserProject.project_id == project.id,
                    UserProject.user_id == member.id,
                )
                .first()
            )
            assert user_project is not None
            assert user_project.role == "admin"
        finally:
            fresh_session.close()


class TestBulkAddMembersEndpoint:
    """Tests for POST /projects/{id}/members/bulk endpoint"""

    def test_bulk_add_members_success(self, client: TestClient, db_session: Session, test_user):
        """Test bulk adding members to project"""
        # Arrange: Create project with authenticated user and new users
        project = ProjectFactory.create(db_session, test_user)
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)

        # Act: Bulk add members
        bulk_data = {
            "users": [
                {"user_id": str(user1.id), "role": "member"},
                {"user_id": str(user2.id), "role": "admin"},
            ]
        }
        response = client.post(f"/api/v1/projects/{project.id}/members/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_processed"] == 2
        assert data["total_success"] == 2

        # Verify in database
        fresh_session = SessionLocal()
        try:
            user_projects = fresh_session.query(UserProject).filter(UserProject.project_id == project.id).all()
            user_ids = [up.user_id for up in user_projects]
            assert user1.id in user_ids
            assert user2.id in user_ids
        finally:
            fresh_session.close()

    def test_bulk_add_members_with_invalid_user(self, client: TestClient, db_session: Session, test_user):
        """Test bulk add with non-existent user"""
        # Arrange: Create project with authenticated user and new user
        project = ProjectFactory.create(db_session, test_user)
        user = UserFactory.create(db_session)
        fake_user_id = uuid.uuid4()

        # Act: Bulk add with one invalid user
        bulk_data = {
            "users": [
                {"user_id": str(user.id), "role": "member"},
                {"user_id": str(fake_user_id), "role": "member"},
            ]
        }
        response = client.post(f"/api/v1/projects/{project.id}/members/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 2
        assert data["total_success"] == 1
        assert data["total_failed"] == 1

    def test_bulk_add_members_requires_admin_access(self, client: TestClient, db_session: Session):
        """Test that only admins can bulk add members"""
        # Arrange: Create project with different creator
        other_creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, other_creator)
        user = UserFactory.create(db_session)

        # Act: Try to bulk add as non-admin
        bulk_data = {"users": [{"user_id": str(user.id), "role": "member"}]}
        response = client.post(f"/api/v1/projects/{project.id}/members/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 403

    def test_bulk_add_members_persists_to_database(self, client: TestClient, db_session: Session, test_user):
        """Test that bulk added members persist to database"""
        # Arrange: Create project with authenticated user and new users
        project = ProjectFactory.create(db_session, test_user)
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)

        # Act: Bulk add members
        bulk_data = {
            "users": [
                {"user_id": str(user1.id), "role": "member"},
                {"user_id": str(user2.id), "role": "admin"},
            ]
        }
        response = client.post(f"/api/v1/projects/{project.id}/members/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            user_project1 = (
                fresh_session.query(UserProject)
                .filter(
                    UserProject.project_id == project.id,
                    UserProject.user_id == user1.id,
                )
                .first()
            )
            user_project2 = (
                fresh_session.query(UserProject)
                .filter(
                    UserProject.project_id == project.id,
                    UserProject.user_id == user2.id,
                )
                .first()
            )
            assert user_project1 is not None
            assert user_project1.role == "member"
            assert user_project2 is not None
            assert user_project2.role == "admin"
        finally:
            fresh_session.close()


class TestBulkRemoveMembersEndpoint:
    """Tests for DELETE /projects/{id}/members/bulk endpoint"""

    def test_bulk_remove_members_success(self, client: TestClient, db_session: Session, test_user):
        """Test bulk removing members from project"""
        # Arrange: Create project with members using authenticated user
        project = ProjectFactory.create(db_session, test_user)
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user1, project=project)
        UserProjectFactory.create(db_session, user=user2, project=project)

        # Act: Bulk remove members
        user_ids = f"{user1.id},{user2.id}"
        response = client.delete(f"/api/v1/projects/{project.id}/members/bulk?user_ids={user_ids}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_processed"] == 2
        assert data["total_success"] == 2

        # Verify removed from database
        user_projects = db_session.query(UserProject).filter(UserProject.project_id == project.id).all()
        user_ids_in_project = [up.user_id for up in user_projects]
        assert user1.id not in user_ids_in_project
        assert user2.id not in user_ids_in_project

    def test_bulk_remove_members_with_invalid_user(self, client: TestClient, db_session: Session, test_user):
        """Test bulk remove with user not in project"""
        # Arrange: Create project with member using authenticated user
        project = ProjectFactory.create(db_session, test_user)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project)
        fake_user_id = uuid.uuid4()

        # Act: Bulk remove with one invalid user
        user_ids = f"{user.id},{fake_user_id}"
        response = client.delete(f"/api/v1/projects/{project.id}/members/bulk?user_ids={user_ids}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 2
        assert data["total_success"] == 1
        assert data["total_failed"] == 1

    def test_bulk_remove_members_requires_admin_access(self, client: TestClient, db_session: Session):
        """Test that only admins can bulk remove members"""
        # Arrange: Create project with different creator
        other_creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, other_creator)
        user = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user, project=project)

        # Act: Try to bulk remove as non-admin
        user_ids = str(user.id)
        response = client.delete(f"/api/v1/projects/{project.id}/members/bulk?user_ids={user_ids}")

        # Assert
        assert response.status_code == 403

    def test_bulk_remove_members_persists_to_database(self, client: TestClient, db_session: Session, test_user):
        """Test that bulk removed members are removed from database"""
        # Arrange: Create project with members using authenticated user
        project = ProjectFactory.create(db_session, test_user)
        user1 = UserFactory.create(db_session)
        user2 = UserFactory.create(db_session)
        UserProjectFactory.create(db_session, user=user1, project=project)
        UserProjectFactory.create(db_session, user=user2, project=project)

        # Act: Bulk remove members
        user_ids = f"{user1.id},{user2.id}"
        response = client.delete(f"/api/v1/projects/{project.id}/members/bulk?user_ids={user_ids}")

        # Assert
        assert response.status_code == 200

        # Verify removed from database with fresh session
        fresh_session = SessionLocal()
        try:
            user_project1 = (
                fresh_session.query(UserProject)
                .filter(
                    UserProject.project_id == project.id,
                    UserProject.user_id == user1.id,
                )
                .first()
            )
            user_project2 = (
                fresh_session.query(UserProject)
                .filter(
                    UserProject.project_id == project.id,
                    UserProject.user_id == user2.id,
                )
                .first()
            )
            assert user_project1 is None
            assert user_project2 is None
        finally:
            fresh_session.close()
