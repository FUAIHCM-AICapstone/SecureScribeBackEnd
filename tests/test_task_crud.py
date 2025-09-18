import uuid
import pytest
from sqlalchemy.orm import Session

from app.models.task import Task, TaskProject
from app.models.project import Project
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.task import (
    create_task,
    get_tasks,
    get_task,
    update_task,
    delete_task,
    bulk_create_tasks,
    bulk_update_tasks,
    bulk_delete_tasks,
    check_task_access,
)


@pytest.fixture
def test_user(db: Session):
    """Create a test user"""
    user = User(email="test@example.com", name="Test User", password_hash="hashed_password")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_project(db: Session, test_user: User):
    """Create a test project"""
    project = Project(
        name="Test Project",
        description="Test project description",
        created_by=test_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Add user to project
    from app.models.project import UserProject

    user_project = UserProject(user_id=test_user.id, project_id=project.id, role="admin")
    db.add(user_project)
    db.commit()

    return project


@pytest.fixture
def test_task(db: Session, test_user: User, test_project: Project):
    """Create a test task"""
    task_data = TaskCreate(
        title="Test Task",
        description="Test task description",
        project_ids=[test_project.id],
    )
    task = create_task(db, task_data, test_user.id)
    return task


class TestTaskCRUD:
    """Test Task CRUD operations"""

    def test_create_task(self, db: Session, test_user: User, test_project: Project):
        """Test creating a task"""
        task_data = TaskCreate(
            title="New Task",
            description="Task description",
            project_ids=[test_project.id],
        )

        task = create_task(db, task_data, test_user.id)

        assert task.title == "New Task"
        assert task.description == "Task description"
        assert task.creator_id == test_user.id
        assert task.status == "todo"

        # Check project link created
        task_project = (
            db.query(TaskProject)
            .filter(
                TaskProject.task_id == task.id,
                TaskProject.project_id == test_project.id,
            )
            .first()
        )
        assert task_project is not None

    def test_create_task_with_assignee(self, db: Session, test_user: User, test_project: Project):
        """Test creating a task with assignee"""
        task_data = TaskCreate(
            title="Assigned Task",
            assignee_id=test_user.id,
            project_ids=[test_project.id],
        )

        task = create_task(db, task_data, test_user.id)

        assert task.assignee_id == test_user.id

    def test_get_tasks(self, db: Session, test_user: User, test_task: Task):
        """Test getting tasks with filtering"""
        tasks, total = get_tasks(db, test_user.id)

        assert total >= 1
        assert len(tasks) >= 1

        # Check task is in results
        task_ids = [t.id for t in tasks]
        assert test_task.id in task_ids

    def test_get_task(self, db: Session, test_user: User, test_task: Task):
        """Test getting single task"""
        task = get_task(db, test_task.id, test_user.id)

        assert task is not None
        assert task.id == test_task.id
        assert task.title == test_task.title

    def test_get_task_no_access(self, db: Session):
        """Test getting task without access"""
        # Create another user
        other_user = User(email="other@example.com", name="Other User")
        db.add(other_user)
        db.commit()

        # Try to access task
        task = get_task(db, uuid.uuid4(), other_user.id)
        assert task is None

    def test_update_task(self, db: Session, test_user: User, test_task: Task):
        """Test updating a task"""
        update_data = TaskUpdate(title="Updated Task", status="in_progress")

        updated_task = update_task(db, test_task.id, update_data, test_user.id)

        assert updated_task.title == "Updated Task"
        assert updated_task.status == "in_progress"

    def test_delete_task(self, db: Session, test_user: User, test_task: Task):
        """Test deleting a task"""
        result = delete_task(db, test_task.id, test_user.id)

        assert result is True

        # Check task is deleted
        deleted_task = db.query(Task).filter(Task.id == test_task.id).first()
        assert deleted_task is None

        # Check project links are deleted
        task_projects = db.query(TaskProject).filter(TaskProject.task_id == test_task.id).all()
        assert len(task_projects) == 0

    def test_check_task_access(self, db: Session, test_user: User, test_task: Task):
        """Test task access checking"""
        # User should have access
        assert check_task_access(db, test_task.id, test_user.id) is True

        # Other user should not have access
        other_user = User(email="other@example.com", name="Other User")
        db.add(other_user)
        db.commit()

        assert check_task_access(db, test_task.id, other_user.id) is False

    def test_bulk_create_tasks(self, db: Session, test_user: User, test_project: Project):
        """Test bulk creating tasks"""
        task_data_list = [TaskCreate(title=f"Task {i}", project_ids=[test_project.id]) for i in range(3)]

        results = bulk_create_tasks(db, task_data_list, test_user.id)

        assert len(results) == 3
        success_count = sum(1 for r in results if r["success"])
        assert success_count == 3

    def test_bulk_update_tasks(self, db: Session, test_user: User, test_project: Project):
        """Test bulk updating tasks"""
        # Create test tasks
        task_data_list = [TaskCreate(title=f"Task {i}", project_ids=[test_project.id]) for i in range(2)]
        results = bulk_create_tasks(db, task_data_list, test_user.id)
        task_ids = [r["id"] for r in results if r["success"]]

        # Update tasks
        updates = [
            {"id": task_ids[0], "updates": TaskUpdate(status="in_progress")},
            {"id": task_ids[1], "updates": TaskUpdate(status="done")},
        ]

        update_results = bulk_update_tasks(db, updates, test_user.id)

        assert len(update_results) == 2
        success_count = sum(1 for r in update_results if r["success"])
        assert success_count == 2

    def test_bulk_delete_tasks(self, db: Session, test_user: User, test_project: Project):
        """Test bulk deleting tasks"""
        # Create test tasks
        task_data_list = [TaskCreate(title=f"Task {i}", project_ids=[test_project.id]) for i in range(2)]
        results = bulk_create_tasks(db, task_data_list, test_user.id)
        task_ids = [r["id"] for r in results if r["success"]]

        # Delete tasks
        delete_results = bulk_delete_tasks(db, task_ids, test_user.id)

        assert len(delete_results) == 2
        success_count = sum(1 for r in delete_results if r["success"])
        assert success_count == 2

    def test_task_filtering(self, db: Session, test_user: User, test_project: Project):
        """Test task filtering"""
        # Create tasks with different statuses
        tasks_data = [
            TaskCreate(title="Todo Task", status="todo", project_ids=[test_project.id]),
            TaskCreate(
                title="In Progress Task",
                status="in_progress",
                project_ids=[test_project.id],
            ),
            TaskCreate(title="Done Task", status="done", project_ids=[test_project.id]),
        ]

        for task_data in tasks_data:
            create_task(db, task_data, test_user.id)

        # Test status filtering
        todo_tasks, _ = get_tasks(db, test_user.id, status="todo")
        assert len(todo_tasks) >= 1
        assert all(t.status == "todo" for t in todo_tasks)

        # Test title search
        search_tasks, _ = get_tasks(db, test_user.id, title="Progress")
        assert len(search_tasks) >= 1
        assert all("Progress" in t.title for t in search_tasks)
