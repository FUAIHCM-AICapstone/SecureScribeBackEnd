"""Integration tests for task workflows"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.main import app
from app.models.task import Task, TaskProject
from app.models.user import User
from app.utils.auth import create_access_token
from tests.factories import ProjectFactory, TaskFactory, UserFactory


class TestTaskCreationAndAssignment:
    """Integration tests for task creation and assignment workflow"""

    def test_task_creation_creates_database_record(self, db_session: Session):
        """Test that task creation creates a record in the database"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()

        task_data = {
            "title": "Test Task",
            "description": "A test task for integration testing",
            "status": "todo",
            "priority": "Cao",
            "project_ids": [],
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == task_data["title"]
        assert data["data"]["description"] == task_data["description"]

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            task_id = uuid.UUID(data["data"]["id"])
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task is not None
            assert db_task.title == task_data["title"]
            assert db_task.creator_id == creator.id
            assert db_task.status == "todo"
        finally:
            fresh_session.close()

    def test_task_creation_with_assignee(self, db_session: Session):
        """Test that task creation with assignee persists correctly"""
        # Arrange
        creator = UserFactory.create(db_session)
        assignee = UserFactory.create(db_session)
        db_session.commit()

        task_data = {
            "title": "Assigned Task",
            "description": "Task with assignee",
            "status": "todo",
            "priority": "Cao",
            "assignee_id": str(assignee.id),
            "project_ids": [],
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["assignee_id"] == str(assignee.id)

        # Verify in database
        fresh_session = SessionLocal()
        try:
            task_id = uuid.UUID(data["data"]["id"])
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task is not None
            assert db_task.assignee_id == assignee.id
        finally:
            fresh_session.close()

    def test_task_creation_with_project_links(self, db_session: Session):
        """Test that task creation with project links persists correctly"""
        # Arrange
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        task_data = {
            "title": "Project Task",
            "description": "Task linked to project",
            "status": "todo",
            "priority": "Cao",
            "project_ids": [str(project.id)],
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        task_id = uuid.UUID(data["data"]["id"])

        # Verify project link in database
        fresh_session = SessionLocal()
        try:
            task_project = (
                fresh_session.query(TaskProject)
                .filter(
                    TaskProject.task_id == task_id,
                    TaskProject.project_id == project.id,
                )
                .first()
            )
            assert task_project is not None
        finally:
            fresh_session.close()


class TestTaskStatusUpdatesAndNotifications:
    """Integration tests for task status updates and notifications"""

    def test_task_status_update_persists_to_database(self, db_session: Session):
        """Test that task status updates persist to database"""
        # Arrange: Create task
        creator = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator=creator, status="todo")
        db_session.commit()

        update_data = {
            "status": "in_progress",
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.put(f"/api/v1/tasks/{task.id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "in_progress"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task.id).first()
            assert db_task is not None
            assert db_task.status == "in_progress"
        finally:
            fresh_session.close()

    def test_task_status_update_from_todo_to_completed(self, db_session: Session):
        """Test task status transition from todo to completed"""
        # Arrange
        creator = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator=creator, status="todo")
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update to in_progress
        response1 = client.put(f"/api/v1/tasks/{task.id}", json={"status": "in_progress"})
        assert response1.status_code == 200

        # Act: Update to completed
        response2 = client.put(f"/api/v1/tasks/{task.id}", json={"status": "completed"})
        assert response2.status_code == 200

        # Assert
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task.id).first()
            assert db_task.status == "completed"
        finally:
            fresh_session.close()

    def test_task_assignee_update_persists(self, db_session: Session):
        """Test that task assignee updates persist to database"""
        # Arrange
        creator = UserFactory.create(db_session)
        assignee1 = UserFactory.create(db_session)
        assignee2 = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator=creator, assignee=assignee1)
        db_session.commit()

        update_data = {
            "assignee_id": str(assignee2.id),
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.put(f"/api/v1/tasks/{task.id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["assignee_id"] == str(assignee2.id)

        # Verify in database
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task.id).first()
            assert db_task.assignee_id == assignee2.id
        finally:
            fresh_session.close()

    def test_task_partial_update(self, db_session: Session):
        """Test updating only some task fields"""
        # Arrange
        creator = UserFactory.create(db_session)
        task = TaskFactory.create(
            db_session,
            creator=creator,
            title="Original Title",
            description="Original description",
            status="todo",
        )
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Update only title
        response = client.put(f"/api/v1/tasks/{task.id}", json={"title": "Updated Title"})

        # Assert
        assert response.status_code == 200

        # Verify other fields unchanged
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task.id).first()
            assert db_task.title == "Updated Title"
            assert db_task.description == "Original description"
            assert db_task.status == "todo"
        finally:
            fresh_session.close()


class TestTaskDeletionAndCleanup:
    """Integration tests for task deletion and cleanup"""

    def test_task_deletion_removes_from_database(self, db_session: Session):
        """Test that task deletion removes task from database"""
        # Arrange: Create task
        creator = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator=creator)
        task_id = task.id
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/tasks/{task_id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deleted from database with fresh session
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task is None
        finally:
            fresh_session.close()

    def test_task_deletion_removes_project_associations(self, db_session: Session):
        """Test that task deletion removes all project associations"""
        # Arrange: Create task with project links
        creator = UserFactory.create(db_session)
        project1 = ProjectFactory.create(db_session, created_by=creator)
        project2 = ProjectFactory.create(db_session, created_by=creator)
        task = TaskFactory.create(db_session, creator=creator)
        task_id = task.id
        db_session.commit()

        # Add project links
        task_project1 = TaskProject(task_id=task.id, project_id=project1.id)
        task_project2 = TaskProject(task_id=task.id, project_id=project2.id)
        db_session.add(task_project1)
        db_session.add(task_project2)
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/tasks/{task_id}")

        # Assert
        assert response.status_code == 200

        # Verify task and all associations deleted
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task is None

            # Verify no task-project associations remain
            task_projects = (
                fresh_session.query(TaskProject)
                .filter(TaskProject.task_id == task_id)
                .all()
            )
            assert len(task_projects) == 0
        finally:
            fresh_session.close()

    def test_task_deletion_by_creator(self, db_session: Session):
        """Test that task creator can delete task"""
        # Arrange
        creator = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator=creator)
        task_id = task.id
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/tasks/{task_id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deleted
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task is None
        finally:
            fresh_session.close()

    def test_task_deletion_by_assignee(self, db_session: Session):
        """Test that task assignee can delete task"""
        # Arrange
        creator = UserFactory.create(db_session)
        assignee = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator=creator, assignee=assignee)
        task_id = task.id
        db_session.commit()

        access_token = create_access_token({"sub": str(assignee.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act
        response = client.delete(f"/api/v1/tasks/{task_id}")

        # Assert
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify deleted
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task is None
        finally:
            fresh_session.close()


class TestTaskWorkflowDataPersistence:
    """Integration tests for task workflow data persistence"""

    def test_task_data_persists_across_sessions(self, db_session: Session):
        """Test that task data persists across database sessions"""
        # Arrange: Create task in one session
        creator = UserFactory.create(db_session)
        task = TaskFactory.create(
            db_session,
            creator=creator,
            title="Persistence Test Task",
            description="Test persistence",
            status="todo",
        )
        task_id = task.id
        db_session.commit()
        db_session.close()

        # Act: Retrieve task in new session
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()

            # Assert
            assert db_task is not None
            assert db_task.title == "Persistence Test Task"
            assert db_task.description == "Test persistence"
            assert db_task.status == "todo"
        finally:
            fresh_session.close()

    def test_task_project_associations_persist(self, db_session: Session):
        """Test that task project associations persist correctly"""
        # Arrange: Create task with project links
        creator = UserFactory.create(db_session)
        projects = [ProjectFactory.create(db_session, created_by=creator) for _ in range(2)]
        project_ids = [p.id for p in projects]
        task = TaskFactory.create(db_session, creator=creator)
        task_id = task.id
        db_session.commit()

        # Add project links
        for project in projects:
            task_project = TaskProject(task_id=task.id, project_id=project.id)
            db_session.add(task_project)

        db_session.commit()
        db_session.close()

        # Act: Retrieve in new session
        fresh_session = SessionLocal()
        try:
            task_projects = (
                fresh_session.query(TaskProject)
                .filter(TaskProject.task_id == task_id)
                .all()
            )

            # Assert
            assert len(task_projects) == 2
            retrieved_project_ids = [tp.project_id for tp in task_projects]
            for project_id in project_ids:
                assert project_id in retrieved_project_ids
        finally:
            fresh_session.close()

    def test_complete_task_workflow_persistence(self, db_session: Session):
        """Test complete task workflow: create, assign, update status, verify persistence"""
        # Arrange
        creator = UserFactory.create(db_session)
        assignee = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, created_by=creator)
        db_session.commit()

        task_data = {
            "title": "Complete Workflow Task",
            "description": "Initial description",
            "status": "todo",
            "priority": "Cao",
            "project_ids": [str(project.id)],
        }

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act 1: Create task
        create_response = client.post("/api/v1/tasks", json=task_data)
        assert create_response.status_code == 200
        task_id = uuid.UUID(create_response.json()["data"]["id"])

        # Act 2: Assign task
        assign_response = client.put(
            f"/api/v1/tasks/{task_id}",
            json={"assignee_id": str(assignee.id)},
        )
        assert assign_response.status_code == 200

        # Act 3: Update status
        status_response = client.put(
            f"/api/v1/tasks/{task_id}",
            json={"status": "in_progress"},
        )
        assert status_response.status_code == 200

        # Assert: Verify all data persisted correctly
        fresh_session = SessionLocal()
        try:
            # Verify task
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task is not None
            assert db_task.title == "Complete Workflow Task"
            assert db_task.description == "Initial description"
            assert db_task.assignee_id == assignee.id
            assert db_task.status == "in_progress"

            # Verify project link
            task_project = (
                fresh_session.query(TaskProject)
                .filter(
                    TaskProject.task_id == task_id,
                    TaskProject.project_id == project.id,
                )
                .first()
            )
            assert task_project is not None
        finally:
            fresh_session.close()

    def test_task_list_retrieval_shows_all_created_tasks(self, db_session: Session):
        """Test that task list retrieval shows all created tasks"""
        # Arrange: Create user and multiple tasks
        creator = UserFactory.create(db_session)
        db_session.commit()

        tasks_data = [
            {
                "title": f"List Task {i}",
                "description": f"Task {i} for list test",
                "status": "todo",
                "priority": "Cao",
                "project_ids": [],
            }
            for i in range(3)
        ]

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Act: Create tasks
        created_ids = []
        for task_data in tasks_data:
            response = client.post("/api/v1/tasks", json=task_data)
            assert response.status_code == 200
            created_ids.append(response.json()["data"]["id"])

        # Act: Retrieve task list
        list_response = client.get("/api/v1/tasks?limit=100")

        # Assert
        assert list_response.status_code == 200
        tasks = list_response.json()["data"]
        retrieved_ids = [t["id"] for t in tasks]
        for created_id in created_ids:
            assert created_id in retrieved_ids

    def test_task_retrieval_by_status_filter(self, db_session: Session):
        """Test that task retrieval with status filter works correctly"""
        # Arrange: Create tasks with different statuses
        creator = UserFactory.create(db_session)
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Create tasks with different statuses
        for status in ["todo", "in_progress", "completed"]:
            task_data = {
                "title": f"Task {status}",
                "description": f"Task with {status} status",
                "status": status,
                "priority": "Cao",
                "project_ids": [],
            }
            response = client.post("/api/v1/tasks", json=task_data)
            assert response.status_code == 200

        # Act: Retrieve tasks with status filter
        response = client.get("/api/v1/tasks?status=in_progress&limit=100")

        # Assert
        assert response.status_code == 200
        tasks = response.json()["data"]
        assert len(tasks) >= 1
        for task in tasks:
            assert task["status"] == "in_progress"

    def test_task_retrieval_by_assignee_filter(self, db_session: Session):
        """Test that task retrieval with assignee filter works correctly"""
        # Arrange: Create tasks with different assignees
        creator = UserFactory.create(db_session)
        assignee1 = UserFactory.create(db_session)
        assignee2 = UserFactory.create(db_session)
        db_session.commit()

        access_token = create_access_token({"sub": str(creator.id)})
        client = TestClient(app)
        client.headers.update({"Authorization": f"Bearer {access_token}"})

        # Create tasks with different assignees
        task_data1 = {
            "title": "Task for assignee1",
            "description": "Assigned to user 1",
            "status": "todo",
            "priority": "Cao",
            "assignee_id": str(assignee1.id),
            "project_ids": [],
        }
        response1 = client.post("/api/v1/tasks", json=task_data1)
        assert response1.status_code == 200

        task_data2 = {
            "title": "Task for assignee2",
            "description": "Assigned to user 2",
            "status": "todo",
            "priority": "Cao",
            "assignee_id": str(assignee2.id),
            "project_ids": [],
        }
        response2 = client.post("/api/v1/tasks", json=task_data2)
        assert response2.status_code == 200

        # Act: Retrieve tasks assigned to assignee1
        response = client.get(f"/api/v1/tasks?assignee_id={assignee1.id}&limit=100")

        # Assert
        assert response.status_code == 200
        tasks = response.json()["data"]
        assert len(tasks) >= 1
        for task in tasks:
            assert task["assignee_id"] == str(assignee1.id)
