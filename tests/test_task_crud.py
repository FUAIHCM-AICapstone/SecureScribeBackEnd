import uuid

import pytest
from faker import Faker
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.task import Task, TaskProject
from app.models.user import User
from app.schemas.task import TaskCreate, TaskUpdate
from app.services.task import (
    bulk_create_tasks,
    bulk_delete_tasks,
    bulk_update_tasks,
    check_task_access,
    create_task,
    delete_task,
    get_task,
    get_tasks,
    update_task,
)

faker = Faker()


@pytest.fixture
def test_user(db: Session):
    """Create a test user"""
    user = User(
        email=faker.email(),
        name=faker.name(),
        password_hash="hashed_password",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_project(db: Session, test_user: User):
    """Create a test project"""
    project = Project(
        name=faker.company(),
        description=faker.text(max_nb_chars=120),
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
        title=faker.sentence(nb_words=3),
        description=faker.text(max_nb_chars=120),
        project_ids=[test_project.id],
    )
    task = create_task(db, task_data, test_user.id)
    return task


class TestTaskCRUD:
    """Test Task CRUD operations"""

    def test_create_task(self, db: Session, test_user: User, test_project: Project):
        """Test creating a task"""
        title = faker.sentence(nb_words=3)
        desc = faker.text(max_nb_chars=100)
        task_data = TaskCreate(
            title=title,
            description=desc,
            project_ids=[test_project.id],
        )

        task = create_task(db, task_data, test_user.id)

        assert task.title == title
        assert task.description == desc
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
            title=faker.sentence(nb_words=4),
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
        other_user = User(email=faker.email(), name=faker.name())
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
        other_user = User(email=faker.email(), name=faker.name())
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
            TaskCreate(title="Todo Task", project_ids=[test_project.id]),
            TaskCreate(title="In Progress Task", project_ids=[test_project.id]),
            TaskCreate(title="Done Task", project_ids=[test_project.id]),
        ]

        created = {}
        for task_data in tasks_data:
            t = create_task(db, task_data, test_user.id)
            created[t.title] = t

        # Update statuses after creation to match new schema
        update_task(db, created["In Progress Task"].id, TaskUpdate(status="in_progress"), test_user.id)
        update_task(db, created["Done Task"].id, TaskUpdate(status="done"), test_user.id)

        # Test status filtering
        todo_tasks, _ = get_tasks(db, test_user.id, status="todo")
        assert len(todo_tasks) >= 1
        assert all(t.status == "todo" for t in todo_tasks)

        # Test title search
        search_tasks, _ = get_tasks(db, test_user.id, title="Progress")
        assert len(search_tasks) >= 1
        assert all("Progress" in t.title for t in search_tasks)

    def test_task_filter_by_due_date_and_created_at(self, db: Session, test_user: User, test_project: Project):
        """Advanced filter: by due_date ranges and created_at ranges"""
        from datetime import datetime, timedelta

        # Create two tasks with different due dates
        t1 = create_task(
            db,
            TaskCreate(
                title=f"Due Soon {faker.word()}",
                project_ids=[test_project.id],
                due_date=(datetime.utcnow() + timedelta(days=1)),
            ),
            test_user.id,
        )
        t2 = create_task(
            db,
            TaskCreate(
                title=f"Due Later {faker.word()}",
                project_ids=[test_project.id],
                due_date=(datetime.utcnow() + timedelta(days=5)),
            ),
            test_user.id,
        )

        # due_date_gte should include both when set to now
        tasks, _ = get_tasks(db, test_user.id, due_date_gte=datetime.utcnow().isoformat())
        ids = {t.id for t in tasks}
        assert t1.id in ids and t2.id in ids

        # due_date_lte with +2 days should include only t1
        tasks, _ = get_tasks(db, test_user.id, due_date_lte=(datetime.utcnow() + timedelta(days=2)).isoformat())
        ids = {t.id for t in tasks}
        assert t1.id in ids and t2.id not in ids

        # created_at_gte in future should include none
        future = (datetime.utcnow() + timedelta(days=10)).isoformat()
        tasks, total = get_tasks(db, test_user.id, created_at_gte=future)
        assert total == 0 and len(tasks) == 0

    def test_tasks_pagination(self, db: Session, test_user: User, test_project: Project):
        """Ensure pagination works and returns expected counts"""
        # Create 7 tasks
        payloads = [TaskCreate(title=f"PTask {i} {faker.word()}", project_ids=[test_project.id]) for i in range(7)]
        for p in payloads:
            create_task(db, p, test_user.id)

        page1, meta1_total = get_tasks(db, test_user.id, page=1, limit=3)
        assert len(page1) == 3

        page2, _ = get_tasks(db, test_user.id, page=2, limit=3)
        assert len(page2) == 3

        page3, _ = get_tasks(db, test_user.id, page=3, limit=3)
        # The last page can have <= limit
        assert len(page3) >= 1

    def test_bulk_update_mixed_success(self, db: Session, test_user: User, test_project: Project):
        """Bulk update where one id is invalid"""
        # Create one real task
        real = create_task(db, TaskCreate(title=f"BMix {faker.word()}", project_ids=[test_project.id]), test_user.id)
        fake = uuid.uuid4()

        updates = [
            {"id": real.id, "updates": TaskUpdate(status="in_progress")},
            {"id": fake, "updates": TaskUpdate(status="done")},
        ]
        results = bulk_update_tasks(db, updates, test_user.id)
        assert len(results) == 2
        assert any(r["success"] and r.get("id") == real.id for r in results)
        assert any((not r["success"]) and r.get("id") == fake for r in results)

    def test_bulk_delete_mixed_success(self, db: Session, test_user: User, test_project: Project):
        """Bulk delete where one id is invalid"""
        real = create_task(db, TaskCreate(title=f"BDel {faker.word()}", project_ids=[test_project.id]), test_user.id)
        fake = uuid.uuid4()
        results = bulk_delete_tasks(db, [real.id, fake], test_user.id)
        assert len(results) == 2
        assert any(r["success"] and r.get("id") == real.id for r in results)
        assert any((not r["success"]) and r.get("id") == fake for r in results)

    def test_assignee_access_without_project_membership(self, db: Session, test_user: User):
        """Assignee should access the task even if not member of project"""
        # Create a separate project and NOT add user as member
        owner = User(email=faker.email(), name=faker.name(), password_hash="hashed_password")
        db.add(owner)
        db.commit()
        db.refresh(owner)

        project = Project(name=faker.company(), description=faker.text(max_nb_chars=80), created_by=owner.id)
        db.add(project)
        db.commit()
        db.refresh(project)

        # Add owner as member to satisfy creator access for create_task validation
        from app.models.project import UserProject

        db.add(UserProject(user_id=owner.id, project_id=project.id, role="admin"))
        db.commit()

        # Create a task assigned to test_user under this project
        t = create_task(
            db,
            TaskCreate(title=f"AssigneeOnly {faker.word()}", assignee_id=test_user.id, project_ids=[project.id]),
            owner.id,
        )

        # Assignee should be able to see the task
        task = get_task(db, t.id, test_user.id)
        assert task is not None and task.id == t.id
