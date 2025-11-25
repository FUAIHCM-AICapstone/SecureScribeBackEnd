"""Integration tests for project workflows"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models.project import Project, UserProject
from app.models.user import User
from app.utils.auth import create_access_token
from tests.factories import ProjectFactory, UserFactory


class TestProjectCreationAndMemberManagement:
    """Integration tests for project creation and member management workflow"""

    def test_project_creation_creates_database_record(self, db_session: Session):
        """Test that project creation creates a record in the database"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()

        project_data = {
            "name": "Test Project",
            "description": "A test project for integration testing",
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post("/api/v1/projects", json=project_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == project_data["name"]
        assert data["data"]["description"] == project_data["description"]

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            project_id = uuid.UUID(data["data"]["id"])
            db_project = fresh_session.query(Project).filter(Project.id == project_id).first()
            assert db_project is not None
            assert db_project.name == project_data["name"]
            assert db_project.created_by == creator.id
        finally:
            fresh_session.close()

    def test_project_creator_becomes_owner(self, db_session: Session):
        """Test that project creator is automatically added as owner"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()

        project_data = {
            "name": "Owner Test Project",
            "description": "Test project ownership",
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post("/api/v1/projects", json=project_data)
        assert response.status_code == 200
        project_id = uuid.UUID(response.json()["data"]["id"])

        # Assert: Verify creator is owner in database
        fresh_session = SessionLocal()
        try:
            user_project = (
                fresh_session.query(UserProject)
                .filter(
                    UserProject.project_id == project_id,
                    UserProject.user_id == creator.id,
                )
                .first()
            )
            assert user_project is not None
            assert user_project.role == "owner"
        finally:
            fresh_session.close()

    def test_add_member_to_project(self, db_session: Session):
        """Test adding a member to a project"""
        # Arrange: Create project and users
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        member_data = {
            "user_id": str(member.id),
            "role": "member",
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post(f"/api/v1/projects/{project.id}/members", json=member_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["user_id"] == str(member.id)
        assert data["data"]["role"] == "member"

        # Verify in database
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
            assert user_project.role == "member"
        finally:
            fresh_session.close()

    def test_remove_member_from_project(self, db_session: Session):
        """Test removing a member from a project"""
        # Arrange: Create project with members
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        # Add member to project
        member_user_project = UserProject(
            user_id=member.id,
            project_id=project.id,
            role="member",
        )
        db_session.add(member_user_project)
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/projects/{project.id}/members/{member.id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify removed from database
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

    def test_bulk_add_members_to_project(self, db_session: Session):
        """Test bulk adding members to a project"""
        # Arrange
        creator = UserFactory.create(db_session)
        members = [UserFactory.create(db_session) for _ in range(3)]
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        bulk_data = {
            "users": [
                {"user_id": str(member.id), "role": "member"}
                for member in members
            ]
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post(f"/api/v1/projects/{project.id}/members/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_success"] == 3
        assert data["total_failed"] == 0

        # Verify all members added to database
        fresh_session = SessionLocal()
        try:
            for member in members:
                user_project = (
                    fresh_session.query(UserProject)
                    .filter(
                        UserProject.project_id == project.id,
                        UserProject.user_id == member.id,
                    )
                    .first()
                )
                assert user_project is not None
                assert user_project.role == "member"
        finally:
            fresh_session.close()



class TestProjectUpdatesAndDeletion:
    """Integration tests for project updates and deletion workflow"""

    def test_project_update_persists_to_database(self, db_session: Session):
        """Test that project updates persist to database"""
        # Arrange: Create project
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        update_data = {
            "name": "Updated Project Name",
            "description": "Updated description",
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.put(f"/api/v1/projects/{project.id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "Updated Project Name"
        assert data["data"]["description"] == "Updated description"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_project = fresh_session.query(Project).filter(Project.id == project.id).first()
            assert db_project is not None
            assert db_project.name == "Updated Project Name"
            assert db_project.description == "Updated description"
        finally:
            fresh_session.close()

    def test_project_partial_update(self, db_session: Session):
        """Test updating only some project fields"""
        # Arrange
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(
            db_session,
            created_by=creator,
            name="Original Name",
            description="Original description",
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update only name
        response = client.put(f"/api/v1/projects/{project.id}", json={"name": "Updated Name"})

        # Assert
        assert response.status_code == 200

        # Verify other fields unchanged
        fresh_session = SessionLocal()
        try:
            db_project = fresh_session.query(Project).filter(Project.id == project.id).first()
            assert db_project.name == "Updated Name"
            assert db_project.description == "Original description"
        finally:
            fresh_session.close()

    def test_project_deletion_removes_from_database(self, db_session: Session):
        """Test that project deletion removes project from database"""
        # Arrange: Create project
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        project_id = project.id
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/projects/{project_id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deleted from database with fresh session
        fresh_session = SessionLocal()
        try:
            db_project = fresh_session.query(Project).filter(Project.id == project_id).first()
            assert db_project is None
        finally:
            fresh_session.close()

    def test_project_deletion_removes_member_associations(self, db_session: Session):
        """Test that project deletion removes all member associations"""
        # Arrange: Create project with members
        creator = UserFactory.create(db_session)
        members = [UserFactory.create(db_session) for _ in range(2)]
        project = ProjectFactory.create(db_session, created_by=creator)
        project_id = project.id
        db_session.commit()

        # Add members to project
        for member in members:
            member_user_project = UserProject(
                user_id=member.id,
                project_id=project.id,
                role="member",
            )
            db_session.add(member_user_project)

        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/projects/{project_id}")

        # Assert
        assert response.status_code == 200

        # Verify project and all associations deleted
        fresh_session = SessionLocal()
        try:
            db_project = fresh_session.query(Project).filter(Project.id == project_id).first()
            assert db_project is None

            # Verify no user-project associations remain
            user_projects = (
                fresh_session.query(UserProject)
                .filter(UserProject.project_id == project_id)
                .all()
            )
            assert len(user_projects) == 0
        finally:
            fresh_session.close()



class TestRoleBasedAccessControl:
    """Integration tests for role-based access control in projects"""

    def test_owner_can_manage_project(self, db_session: Session):
        """Test that owner can update and delete project"""
        # Arrange
        owner = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=owner)
        db_session.commit()

        access_token = create_access_token({"sub": str(owner.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update project
        update_response = client.put(
            f"/api/v1/projects/{project.id}",
            json={"name": "Updated by Owner"},
        )

        # Assert
        assert update_response.status_code == 200
        assert update_response.json()["data"]["name"] == "Updated by Owner"

    def test_admin_can_manage_project(self, db_session: Session):
        """Test that admin can update project"""
        # Arrange
        creator = UserFactory.create(db_session)
        admin = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        # Add admin to project
        admin_user_project = UserProject(
            user_id=admin.id,
            project_id=project.id,
            role="admin",
        )
        db_session.add(admin_user_project)
        db_session.commit()

        access_token = create_access_token({"sub": str(admin.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update project
        update_response = client.put(
            f"/api/v1/projects/{project.id}",
            json={"name": "Updated by Admin"},
        )

        # Assert
        assert update_response.status_code == 200
        assert update_response.json()["data"]["name"] == "Updated by Admin"

    def test_member_cannot_manage_project(self, db_session: Session):
        """Test that member cannot update project"""
        # Arrange
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        # Add member to project
        member_user_project = UserProject(
            user_id=member.id,
            project_id=project.id,
            role="member",
        )
        db_session.add(member_user_project)
        db_session.commit()

        access_token = create_access_token({"sub": str(member.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Try to update project
        update_response = client.put(
            f"/api/v1/projects/{project.id}",
            json={"name": "Updated by Member"},
        )

        # Assert
        assert update_response.status_code == 403

    def test_viewer_cannot_manage_project(self, db_session: Session):
        """Test that viewer cannot update project"""
        # Arrange
        creator = UserFactory.create(db_session)
        viewer = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        # Add viewer to project
        viewer_user_project = UserProject(
            user_id=viewer.id,
            project_id=project.id,
            role="viewer",
        )
        db_session.add(viewer_user_project)
        db_session.commit()

        access_token = create_access_token({"sub": str(viewer.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Try to update project
        update_response = client.put(
            f"/api/v1/projects/{project.id}",
            json={"name": "Updated by Viewer"},
        )

        # Assert
        assert update_response.status_code == 403

    def test_owner_can_add_members(self, db_session: Session):
        """Test that owner can add members to project"""
        # Arrange
        owner = UserFactory.create(db_session)
        new_member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=owner)
        db_session.commit()

        member_data = {
            "user_id": str(new_member.id),
            "role": "member",
        }

        access_token = create_access_token({"sub": str(owner.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post(f"/api/v1/projects/{project.id}/members", json=member_data)

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_member_cannot_add_members(self, db_session: Session):
        """Test that member cannot add members to project"""
        # Arrange
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        new_member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        # Add member to project
        member_user_project = UserProject(
            user_id=member.id,
            project_id=project.id,
            role="member",
        )
        db_session.add(member_user_project)
        db_session.commit()

        member_data = {
            "user_id": str(new_member.id),
            "role": "member",
        }

        access_token = create_access_token({"sub": str(member.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post(f"/api/v1/projects/{project.id}/members", json=member_data)

        # Assert
        assert response.status_code == 403

    def test_owner_can_remove_members(self, db_session: Session):
        """Test that owner can remove members from project"""
        # Arrange
        owner = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=owner)
        db_session.commit()

        # Add member to project
        member_user_project = UserProject(
            user_id=member.id,
            project_id=project.id,
            role="member",
        )
        db_session.add(member_user_project)
        db_session.commit()

        access_token = create_access_token({"sub": str(owner.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/projects/{project.id}/members/{member.id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_member_cannot_remove_other_members(self, db_session: Session):
        """Test that member cannot remove other members from project"""
        # Arrange
        creator = UserFactory.create(db_session)
        member1 = UserFactory.create(db_session)
        member2 = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        # Add members to project
        member1_user_project = UserProject(
            user_id=member1.id,
            project_id=project.id,
            role="member",
        )
        member2_user_project = UserProject(
            user_id=member2.id,
            project_id=project.id,
            role="member",
        )
        db_session.add(member1_user_project)
        db_session.add(member2_user_project)
        db_session.commit()

        access_token = create_access_token({"sub": str(member1.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/projects/{project.id}/members/{member2.id}")

        # Assert
        assert response.status_code == 403

    def test_member_can_leave_project(self, db_session: Session):
        """Test that member can leave project (self-removal)"""
        # Arrange
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        # Add member to project
        member_user_project = UserProject(
            user_id=member.id,
            project_id=project.id,
            role="member",
        )
        db_session.add(member_user_project)
        db_session.commit()

        access_token = create_access_token({"sub": str(member.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Member removes themselves
        response = client.delete(f"/api/v1/projects/{project.id}/members/{member.id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify removed from database
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



class TestProjectWorkflowDataPersistence:
    """Integration tests for project workflow data persistence"""

    def test_project_data_persists_across_sessions(self, db_session: Session):
        """Test that project data persists across database sessions"""
        # Arrange: Create project in one session
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(
            db_session,
            created_by=creator,
            name="Persistence Test Project",
            description="Test persistence",
        )
        project_id = project.id
        db_session.commit()
        db_session.close()

        # Act: Retrieve project in new session
        fresh_session = SessionLocal()
        try:
            db_project = fresh_session.query(Project).filter(Project.id == project_id).first()

            # Assert
            assert db_project is not None
            assert db_project.name == "Persistence Test Project"
            assert db_project.description == "Test persistence"
        finally:
            fresh_session.close()

    def test_project_member_associations_persist(self, db_session: Session):
        """Test that project member associations persist correctly"""
        # Arrange: Create project with members
        creator = UserFactory.create(db_session)
        creator_id = creator.id
        members = [UserFactory.create(db_session) for _ in range(2)]
        member_ids = [m.id for m in members]
        project = ProjectFactory.create(db_session, created_by=creator)
        project_id = project.id
        db_session.commit()

        # Add members to project
        for i, member in enumerate(members):
            member_user_project = UserProject(
                user_id=member.id,
                project_id=project.id,
                role="member" if i == 0 else "viewer",
            )
            db_session.add(member_user_project)

        db_session.commit()
        db_session.close()

        # Act: Retrieve in new session
        fresh_session = SessionLocal()
        try:
            user_projects = (
                fresh_session.query(UserProject)
                .filter(UserProject.project_id == project_id)
                .all()
            )

            # Assert
            assert len(user_projects) == 3  # creator (owner) + 2 members
            roles = {up.user_id: up.role for up in user_projects}
            assert roles[creator_id] == "owner"
            assert roles[member_ids[0]] == "member"
            assert roles[member_ids[1]] == "viewer"
        finally:
            fresh_session.close()

    def test_complete_project_workflow_persistence(self, db_session: Session):
        """Test complete project workflow: create, add members, update, verify persistence"""
        # Arrange
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        db_session.commit()

        project_data = {
            "name": "Complete Workflow Project",
            "description": "Initial description",
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act 1: Create project
        create_response = client.post("/api/v1/projects", json=project_data)
        assert create_response.status_code == 200
        project_id = uuid.UUID(create_response.json()["data"]["id"])

        # Act 2: Add member
        member_data = {
            "user_id": str(member.id),
            "role": "member",
        }
        add_response = client.post(f"/api/v1/projects/{project_id}/members", json=member_data)
        assert add_response.status_code == 200

        # Act 3: Update project
        update_data = {
            "name": "Updated Workflow Project",
            "description": "Updated description",
        }
        update_response = client.put(f"/api/v1/projects/{project_id}", json=update_data)
        assert update_response.status_code == 200

        # Assert: Verify all data persisted correctly
        fresh_session = SessionLocal()
        try:
            # Verify project
            db_project = fresh_session.query(Project).filter(Project.id == project_id).first()
            assert db_project is not None
            assert db_project.name == "Updated Workflow Project"
            assert db_project.description == "Updated description"

            # Verify members
            user_projects = (
                fresh_session.query(UserProject)
                .filter(UserProject.project_id == project_id)
                .all()
            )
            assert len(user_projects) == 2
            roles = {up.user_id: up.role for up in user_projects}
            assert roles[creator.id] == "owner"
            assert roles[member.id] == "member"
        finally:
            fresh_session.close()

    def test_project_list_retrieval_shows_all_created_projects(self, db_session: Session):
        """Test that project list retrieval shows all created projects"""
        # Arrange: Create user and multiple projects
        creator = UserFactory.create(db_session)
        db_session.commit()

        projects_data = [
            {
                "name": f"List Project {i}",
                "description": f"Project {i} for list test",
            }
            for i in range(3)
        ]

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Create projects
        created_ids = []
        for project_data in projects_data:
            response = client.post("/api/v1/projects", json=project_data)
            assert response.status_code == 200
            created_ids.append(response.json()["data"]["id"])

        # Act: Retrieve project list
        list_response = client.get("/api/v1/projects?limit=100")

        # Assert
        assert list_response.status_code == 200
        projects = list_response.json()["data"]
        retrieved_ids = [p["id"] for p in projects]
        for created_id in created_ids:
            assert created_id in retrieved_ids

    def test_role_changes_persist_correctly(self, db_session: Session):
        """Test that role changes persist correctly in database"""
        # Arrange
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        # Add member to project
        member_user_project = UserProject(
            user_id=member.id,
            project_id=project.id,
            role="member",
        )
        db_session.add(member_user_project)
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update member role
        role_update = {"role": "admin"}
        response = client.put(
            f"/api/v1/projects/{project.id}/members/{member.id}",
            json=role_update,
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["data"]["role"] == "admin"

        # Verify in database
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
