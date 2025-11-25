"""API endpoint tests for task management"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.task import Task, TaskProject
from app.db import SessionLocal
from app.utils.auth import create_access_token
from app.main import app
from tests.factories import (
    TaskFactory,
    UserFactory,
    ProjectFactory,
    MeetingFactory,
    TaskProjectFactory,
)


def create_authenticated_client(user_id: uuid.UUID) -> TestClient:
    """Helper to create an authenticated test client for a user"""
    token_data = {"sub": str(user_id)}
    access_token = create_access_token(token_data)
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {access_token}"})
    return client


class TestGetTasksEndpoint:
    """Tests for GET /tasks endpoint"""

    def test_get_tasks_returns_paginated_list(self, db_session: Session):
        """Test that GET /tasks returns paginated list of tasks"""
        # Arrange: Create test user and tasks
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        for _ in range(5):
            TaskFactory.create(db_session, creator)
        db_session.commit()

        client = create_authenticated_client(creator.id)

        # Act: Get tasks
        response = client.get("/api/v1/tasks?page=1&limit=10")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) >= 5
        assert data["pagination"]["total"] >= 5

    def test_get_tasks_with_pagination(self, db_session: Session):
        """Test that pagination works correctly"""
        # Arrange: Create 15 test tasks
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        for i in range(15):
            TaskFactory.create(db_session, creator, title=f"Task {i}")
        db_session.commit()

        client = create_authenticated_client(creator.id)

        # Act: Get first page with limit 5
        response = client.get("/api/v1/tasks?page=1&limit=5")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) == 5
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["limit"] == 5

    def test_get_tasks_with_title_filter(self, db_session: Session):
        """Test that title filter works correctly"""
        # Arrange: Create tasks with specific titles
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        TaskFactory.create(db_session, creator, title="Important Task")
        TaskFactory.create(db_session, creator, title="Other Task")
        db_session.commit()

        client = create_authenticated_client(creator.id)

        # Act: Filter by title
        response = client.get("/api/v1/tasks?title=Important")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert any(t["title"] == "Important Task" for t in data["data"])

    def test_get_tasks_with_status_filter(self, db_session: Session):
        """Test that status filter works correctly"""
        # Arrange: Create tasks with different statuses
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        TaskFactory.create(db_session, creator, status="todo")
        TaskFactory.create(db_session, creator, status="in_progress")
        db_session.commit()

        client = create_authenticated_client(creator.id)

        # Act: Filter by status
        response = client.get("/api/v1/tasks?status=todo")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1
        assert all(t["status"] == "todo" for t in data["data"])

    def test_get_tasks_access_control(self, db_session: Session):
        """Test that users only see tasks they have access to"""
        # Arrange: Create tasks by different users
        creator1 = UserFactory.create(db_session)
        creator2 = UserFactory.create(db_session)
        db_session.commit()
        
        task1 = TaskFactory.create(db_session, creator1)
        task2 = TaskFactory.create(db_session, creator2)
        db_session.commit()

        client = create_authenticated_client(creator1.id)

        # Act: Get tasks as creator1
        response = client.get("/api/v1/tasks")

        # Assert
        assert response.status_code == 200
        data = response.json()
        # Should see own tasks
        task_ids = {t["id"] for t in data["data"]}
        assert str(task1.id) in task_ids


class TestCreateTaskEndpoint:
    """Tests for POST /tasks endpoint"""

    def test_create_task_with_valid_data(self, db_session: Session):
        """Test creating a task with valid data"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        project = ProjectFactory.create(db_session, creator)
        db_session.commit()
        
        task_data = {
            "title": "New Task",
            "description": "A new test task",
            "project_ids": [str(project.id)],
        }

        client = create_authenticated_client(creator.id)

        # Act
        response = client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == "New Task"
        assert data["data"]["description"] == "A new test task"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == uuid.UUID(data["data"]["id"])).first()
            assert db_task is not None
            assert db_task.title == "New Task"
            assert db_task.description == "A new test task"
        finally:
            fresh_session.close()

    def test_create_task_with_assignee(self, db_session: Session):
        """Test creating a task with assignee"""
        # Arrange
        creator = UserFactory.create(db_session)
        assignee = UserFactory.create(db_session)
        db_session.commit()
        
        project = ProjectFactory.create(db_session, creator)
        db_session.commit()
        
        task_data = {
            "title": "Assigned Task",
            "assignee_id": str(assignee.id),
            "project_ids": [str(project.id)],
        }

        client = create_authenticated_client(creator.id)

        # Act
        response = client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["assignee_id"] == str(assignee.id)

        # Verify in database
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == uuid.UUID(data["data"]["id"])).first()
            assert db_task.assignee_id == assignee.id
        finally:
            fresh_session.close()

    def test_create_task_with_meeting(self, db_session: Session):
        """Test creating a task linked to a meeting"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        project = ProjectFactory.create(db_session, creator)
        meeting = MeetingFactory.create(db_session, creator)
        db_session.commit()
        
        task_data = {
            "title": "Meeting Task",
            "meeting_id": str(meeting.id),
            "project_ids": [str(project.id)],
        }

        client = create_authenticated_client(creator.id)

        # Act
        response = client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["meeting_id"] == str(meeting.id)

        # Verify in database
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == uuid.UUID(data["data"]["id"])).first()
            assert db_task.meeting_id == meeting.id
        finally:
            fresh_session.close()

    def test_create_task_with_multiple_projects(self, db_session: Session):
        """Test creating a task linked to multiple projects"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        project1 = ProjectFactory.create(db_session, creator)
        project2 = ProjectFactory.create(db_session, creator)
        db_session.commit()
        
        task_data = {
            "title": "Multi-Project Task",
            "project_ids": [str(project1.id), str(project2.id)],
        }

        client = create_authenticated_client(creator.id)

        # Act
        response = client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]["projects"]) == 2

        # Verify in database
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == uuid.UUID(data["data"]["id"])).first()
            task_projects = fresh_session.query(TaskProject).filter(TaskProject.task_id == db_task.id).all()
            assert len(task_projects) == 2
        finally:
            fresh_session.close()

    def test_create_task_no_access_to_project(self, db_session: Session):
        """Test creating task without access to project fails"""
        # Arrange
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        db_session.commit()
        
        project = ProjectFactory.create(db_session, other_user)
        db_session.commit()
        
        task_data = {
            "title": "Unauthorized Task",
            "project_ids": [str(project.id)],
        }

        client = create_authenticated_client(creator.id)

        # Act
        response = client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert response.status_code == 403

    def test_create_task_no_access_to_meeting(self, db_session: Session):
        """Test creating task without access to meeting fails"""
        # Arrange
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        db_session.commit()
        
        project = ProjectFactory.create(db_session, creator)
        meeting = MeetingFactory.create(db_session, other_user)
        db_session.commit()
        
        task_data = {
            "title": "Unauthorized Meeting Task",
            "meeting_id": str(meeting.id),
            "project_ids": [str(project.id)],
        }

        client = create_authenticated_client(creator.id)

        # Act
        response = client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert response.status_code == 403

    def test_create_task_persists_to_database(self, db_session: Session):
        """Test that created task is persisted to database"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        project = ProjectFactory.create(db_session, creator)
        db_session.commit()
        
        task_data = {
            "title": "Persist Task",
            "description": "Should persist",
            "status": "in_progress",
            "project_ids": [str(project.id)],
        }

        client = create_authenticated_client(creator.id)

        # Act
        response = client.post("/api/v1/tasks", json=task_data)

        # Assert
        assert response.status_code == 200
        task_id = response.json()["data"]["id"]

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == uuid.UUID(task_id)).first()
            assert db_task is not None
            assert db_task.title == "Persist Task"
            assert db_task.description == "Should persist"
            assert db_task.status == "in_progress"
        finally:
            fresh_session.close()


class TestUpdateTaskEndpoint:
    """Tests for PUT /tasks/{id} endpoint"""

    def test_update_task_with_valid_data(self, db_session: Session):
        """Test updating a task with valid data"""
        # Arrange: Create task
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        task = TaskFactory.create(db_session, creator, title="Original Title")
        db_session.commit()
        
        task_id = task.id

        client = create_authenticated_client(creator.id)

        # Act: Update task
        update_data = {"title": "Updated Title", "description": "Updated description"}
        response = client.put(f"/api/v1/tasks/{task_id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == "Updated Title"
        assert data["data"]["description"] == "Updated description"

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task.title == "Updated Title"
            assert db_task.description == "Updated description"
        finally:
            fresh_session.close()

    def test_update_task_status(self, db_session: Session):
        """Test updating task status"""
        # Arrange: Create task
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        task = TaskFactory.create(db_session, creator, status="todo")
        db_session.commit()
        
        task_id = task.id

        client = create_authenticated_client(creator.id)

        # Act: Update status
        update_data = {"status": "in_progress"}
        response = client.put(f"/api/v1/tasks/{task_id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "in_progress"

        # Verify in database
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task.status == "in_progress"
        finally:
            fresh_session.close()

    def test_update_task_assignee(self, db_session: Session):
        """Test updating task assignee"""
        # Arrange: Create task
        creator = UserFactory.create(db_session)
        assignee = UserFactory.create(db_session)
        db_session.commit()
        
        task = TaskFactory.create(db_session, creator)
        db_session.commit()
        
        task_id = task.id

        client = create_authenticated_client(creator.id)

        # Act: Update assignee
        update_data = {"assignee_id": str(assignee.id)}
        response = client.put(f"/api/v1/tasks/{task_id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["assignee_id"] == str(assignee.id)

        # Verify in database
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task.assignee_id == assignee.id
        finally:
            fresh_session.close()

    def test_update_task_partial_fields(self, db_session: Session):
        """Test updating only some fields"""
        # Arrange: Create task
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        original_desc = "Original description"
        task = TaskFactory.create(db_session, creator, description=original_desc)
        db_session.commit()
        
        task_id = task.id

        client = create_authenticated_client(creator.id)

        # Act: Update only title
        update_data = {"title": "New Title"}
        response = client.put(f"/api/v1/tasks/{task_id}", json=update_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "New Title"

        # Verify description unchanged
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task.description == original_desc
        finally:
            fresh_session.close()

    def test_update_task_no_access(self, db_session: Session):
        """Test updating a task without access fails"""
        # Arrange
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        db_session.commit()
        
        task = TaskFactory.create(db_session, creator)
        db_session.commit()

        client = create_authenticated_client(other_user.id)

        # Act
        response = client.put(f"/api/v1/tasks/{task.id}", json={"title": "Updated"})

        # Assert
        assert response.status_code == 403

    def test_update_task_persists_to_database(self, db_session: Session):
        """Test that task updates persist to database"""
        # Arrange: Create task
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        task = TaskFactory.create(db_session, creator, status="todo")
        db_session.commit()
        
        task_id = task.id

        client = create_authenticated_client(creator.id)

        # Act: Update status
        update_data = {"status": "completed"}
        response = client.put(f"/api/v1/tasks/{task_id}", json=update_data)

        # Assert
        assert response.status_code == 200

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task.status == "completed"
        finally:
            fresh_session.close()


class TestDeleteTaskEndpoint:
    """Tests for DELETE /tasks/{id} endpoint"""

    def test_delete_task_success(self, db_session: Session):
        """Test deleting a task successfully"""
        # Arrange: Create task
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        task = TaskFactory.create(db_session, creator)
        db_session.commit()
        
        task_id = task.id

        client = create_authenticated_client(creator.id)

        # Act: Delete task
        response = client.delete(f"/api/v1/tasks/{task_id}")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Verify removed from database
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task is None
        finally:
            fresh_session.close()

    def test_delete_task_cascade_deletes_project_links(self, db_session: Session):
        """Test deleting a task removes project links"""
        # Arrange: Create task with project link
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        project = ProjectFactory.create(db_session, creator)
        task = TaskFactory.create(db_session, creator)
        TaskProjectFactory.create(db_session, task, project)
        db_session.commit()
        
        task_id = task.id

        client = create_authenticated_client(creator.id)

        # Act: Delete task
        response = client.delete(f"/api/v1/tasks/{task_id}")

        # Assert
        assert response.status_code == 200

        # Verify project links removed
        fresh_session = SessionLocal()
        try:
            task_projects = fresh_session.query(TaskProject).filter(TaskProject.task_id == task_id).all()
            assert len(task_projects) == 0
        finally:
            fresh_session.close()

    def test_delete_task_no_access(self, db_session: Session):
        """Test deleting a task without access fails"""
        # Arrange
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        db_session.commit()
        
        task = TaskFactory.create(db_session, creator)
        db_session.commit()

        client = create_authenticated_client(other_user.id)

        # Act
        response = client.delete(f"/api/v1/tasks/{task.id}")

        # Assert
        assert response.status_code == 403

    def test_delete_task_removes_from_database(self, db_session: Session):
        """Test that deleted task is removed from database"""
        # Arrange: Create task
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        task = TaskFactory.create(db_session, creator)
        db_session.commit()
        
        task_id = task.id

        # Verify task exists
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task is not None
        finally:
            fresh_session.close()

        client = create_authenticated_client(creator.id)

        # Act: Delete task
        response = client.delete(f"/api/v1/tasks/{task_id}")

        # Assert
        assert response.status_code == 200

        # Verify removed from database
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.id == task_id).first()
            assert db_task is None
        finally:
            fresh_session.close()


class TestBulkCreateTasksEndpoint:
    """Tests for POST /tasks/bulk endpoint"""

    def test_bulk_create_tasks_success(self, db_session: Session):
        """Test bulk creating multiple tasks"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        project = ProjectFactory.create(db_session, creator)
        db_session.commit()
        
        bulk_data = {
            "tasks": [
                {"title": "Bulk Task 1", "project_ids": [str(project.id)]},
                {"title": "Bulk Task 2", "project_ids": [str(project.id)]},
                {"title": "Bulk Task 3", "project_ids": [str(project.id)]},
            ]
        }

        client = create_authenticated_client(creator.id)

        # Act
        response = client.post("/api/v1/tasks/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 3
        assert data["total_success"] == 3
        assert data["total_failed"] == 0

        # Verify all tasks in database with fresh session
        fresh_session = SessionLocal()
        try:
            for task_data in bulk_data["tasks"]:
                db_task = fresh_session.query(Task).filter(Task.title == task_data["title"]).first()
                assert db_task is not None
        finally:
            fresh_session.close()

    def test_bulk_create_tasks_partial_failure(self, db_session: Session):
        """Test bulk create with some failures"""
        # Arrange
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        db_session.commit()
        
        project1 = ProjectFactory.create(db_session, creator)
        project2 = ProjectFactory.create(db_session, other_user)
        db_session.commit()
        
        bulk_data = {
            "tasks": [
                {"title": "Valid Task", "project_ids": [str(project1.id)]},
                {"title": "Invalid Task", "project_ids": [str(project2.id)]},  # No access
            ]
        }

        client = create_authenticated_client(creator.id)

        # Act
        response = client.post("/api/v1/tasks/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_processed"] == 2
        assert data["total_success"] == 1
        assert data["total_failed"] == 1

        # Verify valid task was created
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.title == "Valid Task").first()
            assert db_task is not None
        finally:
            fresh_session.close()

    def test_bulk_create_tasks_persists_to_database(self, db_session: Session):
        """Test that bulk created tasks persist to database"""
        # Arrange
        creator = UserFactory.create(db_session)
        db_session.commit()
        
        project = ProjectFactory.create(db_session, creator)
        db_session.commit()
        
        # Use unique titles to avoid conflicts with other tests
        unique_suffix = uuid.uuid4().hex[:8]
        title1 = f"Persist Task 1 {unique_suffix}"
        title2 = f"Persist Task 2 {unique_suffix}"
        
        bulk_data = {
            "tasks": [
                {"title": title1, "project_ids": [str(project.id)]},
                {"title": title2, "project_ids": [str(project.id)]},
            ]
        }

        client = create_authenticated_client(creator.id)

        # Act
        response = client.post("/api/v1/tasks/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_success"] == 2

        # Verify in database with fresh session
        fresh_session = SessionLocal()
        try:
            count = fresh_session.query(Task).filter(
                Task.title.in_([title1, title2])
            ).count()
            assert count == 2
        finally:
            fresh_session.close()

    def test_bulk_create_tasks_with_relationships(self, db_session: Session):
        """Test bulk create maintains task relationships"""
        # Arrange
        creator = UserFactory.create(db_session)
        assignee = UserFactory.create(db_session)
        db_session.commit()
        
        project = ProjectFactory.create(db_session, creator)
        db_session.commit()
        
        # Use unique title to avoid conflicts with other tests
        unique_suffix = uuid.uuid4().hex[:8]
        task_title = f"Task with Assignee {unique_suffix}"
        
        bulk_data = {
            "tasks": [
                {
                    "title": task_title,
                    "assignee_id": str(assignee.id),
                    "project_ids": [str(project.id)],
                },
            ]
        }

        client = create_authenticated_client(creator.id)

        # Act
        response = client.post("/api/v1/tasks/bulk", json=bulk_data)

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["total_success"] == 1

        # Verify relationships in database
        fresh_session = SessionLocal()
        try:
            db_task = fresh_session.query(Task).filter(Task.title == task_title).first()
            assert db_task is not None, f"Task with title '{task_title}' not found"
            assert db_task.assignee_id == assignee.id, f"Expected assignee_id {assignee.id}, got {db_task.assignee_id}"
        finally:
            fresh_session.close()
