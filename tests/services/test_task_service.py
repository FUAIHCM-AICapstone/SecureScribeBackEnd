"""Unit tests for task service functions"""

import uuid

import pytest
from faker import Faker
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.task import Task, TaskProject
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
from tests.factories import (
    MeetingFactory,
    ProjectFactory,
    TaskFactory,
    TaskProjectFactory,
    UserFactory,
)

fake = Faker()


class TestCreateTask:
    """Tests for create_task function"""

    def test_create_task_success(self, db_session: Session):
        """Test creating a task with valid data"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)

        task_data = TaskCreate(
            title=fake.sentence(nb_words=3),
            description=fake.paragraph(),
            project_ids=[project.id],
        )

        task = create_task(db_session, task_data, creator.id)

        assert task.id is not None
        assert task.title == task_data.title
        assert task.description == task_data.description
        assert task.creator_id == creator.id
        assert task.status == "todo"

    def test_create_task_with_assignee(self, db_session: Session):
        """Test creating a task with assignee"""
        creator = UserFactory.create(db_session)
        assignee = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)

        task_data = TaskCreate(
            title=fake.sentence(nb_words=2),
            assignee_id=assignee.id,
            project_ids=[project.id],
        )

        task = create_task(db_session, task_data, creator.id)

        assert task.assignee_id == assignee.id
        assert task.creator_id == creator.id

    def test_create_task_with_meeting(self, db_session: Session):
        """Test creating a task linked to a meeting"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        meeting = MeetingFactory.create(db_session, creator)

        task_data = TaskCreate(
            title=fake.sentence(nb_words=2),
            meeting_id=meeting.id,
            project_ids=[project.id],
        )

        task = create_task(db_session, task_data, creator.id)

        assert task.meeting_id == meeting.id
        assert task.creator_id == creator.id

    def test_create_task_no_access_to_project(self, db_session: Session):
        """Test creating a task without access to project raises error"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, other_user)

        task_data = TaskCreate(
            title=fake.sentence(nb_words=2),
            project_ids=[project.id],
        )

        with pytest.raises(HTTPException) as exc_info:
            create_task(db_session, task_data, creator.id)

        assert exc_info.value.status_code == 403

    def test_create_task_no_access_to_meeting(self, db_session: Session):
        """Test creating a task without access to meeting raises error"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        meeting = MeetingFactory.create(db_session, other_user)

        task_data = TaskCreate(
            title=fake.sentence(nb_words=3),
            meeting_id=meeting.id,
            project_ids=[project.id],
        )

        with pytest.raises(HTTPException) as exc_info:
            create_task(db_session, task_data, creator.id)

        assert exc_info.value.status_code == 403

    def test_create_task_with_multiple_projects(self, db_session: Session):
        """Test creating a task linked to multiple projects"""
        creator = UserFactory.create(db_session)
        project1 = ProjectFactory.create(db_session, creator)
        project2 = ProjectFactory.create(db_session, creator)

        task_data = TaskCreate(
            title=fake.sentence(nb_words=3),
            project_ids=[project1.id, project2.id],
        )

        task = create_task(db_session, task_data, creator.id)

        # Verify task is linked to both projects
        task_projects = db_session.query(TaskProject).filter(TaskProject.task_id == task.id).all()
        assert len(task_projects) == 2
        project_ids = {tp.project_id for tp in task_projects}
        assert project_ids == {project1.id, project2.id}


class TestUpdateTask:
    """Tests for update_task function"""

    def test_update_task_success(self, db_session: Session):
        """Test updating a task with valid data"""
        creator = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator, title="Original Title")

        task_data = TaskUpdate(
            title=fake.sentence(nb_words=2),
            description=fake.paragraph(),
        )

        updated_task = update_task(db_session, task.id, task_data, creator.id)

        assert updated_task.title == task_data.title
        assert updated_task.description == task_data.description

    def test_update_task_status(self, db_session: Session):
        """Test updating task status"""
        creator = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator, status="todo")

        task_data = TaskUpdate(status="in_progress")

        updated_task = update_task(db_session, task.id, task_data, creator.id)

        assert updated_task.status == "in_progress"

    def test_update_task_assignee(self, db_session: Session):
        """Test updating task assignee"""
        creator = UserFactory.create(db_session)
        assignee = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator)

        task_data = TaskUpdate(assignee_id=assignee.id)

        updated_task = update_task(db_session, task.id, task_data, creator.id)

        assert updated_task.assignee_id == assignee.id

    def test_update_task_no_access(self, db_session: Session):
        """Test updating a task without access raises error"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator)

        task_data = TaskUpdate(title=fake.sentence(nb_words=2))

        with pytest.raises(HTTPException) as exc_info:
            update_task(db_session, task.id, task_data, other_user.id)

        assert exc_info.value.status_code == 403

    def test_update_nonexistent_task(self, db_session: Session):
        """Test updating a nonexistent task raises error"""
        creator = UserFactory.create(db_session)
        fake_task_id = uuid.uuid4()

        task_data = TaskUpdate(title=fake.sentence(nb_words=2))

        with pytest.raises(HTTPException) as exc_info:
            update_task(db_session, fake_task_id, task_data, creator.id)

        # Access check happens before existence check, so returns 403
        assert exc_info.value.status_code == 403

    def test_update_task_partial(self, db_session: Session):
        """Test partial task update only changes specified fields"""
        creator = UserFactory.create(db_session)
        original_desc = "Original description"
        task = TaskFactory.create(db_session, creator, description=original_desc)

        task_data = TaskUpdate(title=fake.sentence(nb_words=2))

        updated_task = update_task(db_session, task.id, task_data, creator.id)

        assert updated_task.title == task_data.title
        assert updated_task.description == original_desc


class TestDeleteTask:
    """Tests for delete_task function"""

    def test_delete_task_success(self, db_session: Session):
        """Test deleting a task"""
        creator = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator)
        task_id = task.id

        result = delete_task(db_session, task_id, creator.id)

        assert result is True
        deleted_task = db_session.query(Task).filter(Task.id == task_id).first()
        assert deleted_task is None

    def test_delete_task_cascade_deletes_project_links(self, db_session: Session):
        """Test deleting a task removes project links"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        task = TaskFactory.create(db_session, creator)
        TaskProjectFactory.create(db_session, task, project)

        delete_task(db_session, task.id, creator.id)

        task_projects = db_session.query(TaskProject).filter(TaskProject.task_id == task.id).all()
        assert len(task_projects) == 0

    def test_delete_task_no_access(self, db_session: Session):
        """Test deleting a task without access raises error"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator)

        with pytest.raises(HTTPException) as exc_info:
            delete_task(db_session, task.id, other_user.id)

        assert exc_info.value.status_code == 403

    def test_delete_nonexistent_task(self, db_session: Session):
        """Test deleting a nonexistent task raises error"""
        creator = UserFactory.create(db_session)
        fake_task_id = uuid.uuid4()

        with pytest.raises(HTTPException) as exc_info:
            delete_task(db_session, fake_task_id, creator.id)

        # Access check happens before existence check, so returns 403
        assert exc_info.value.status_code == 403


class TestGetTasks:
    """Tests for get_tasks function"""

    def test_get_tasks_for_creator(self, db_session: Session):
        """Test retrieving tasks created by user"""
        creator = UserFactory.create(db_session)
        task1 = TaskFactory.create(db_session, creator, title=fake.sentence(nb_words=2))
        task2 = TaskFactory.create(db_session, creator, title=fake.sentence(nb_words=2))

        tasks, total = get_tasks(db_session, creator.id)

        assert total >= 2
        task_ids = {t.id for t in tasks}
        assert task1.id in task_ids
        assert task2.id in task_ids

    def test_get_tasks_for_assignee(self, db_session: Session):
        """Test retrieving tasks assigned to user"""
        creator = UserFactory.create(db_session)
        assignee = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        task = TaskFactory.create(db_session, creator, assignee=assignee)
        TaskProjectFactory.create(db_session, task, project)

        tasks, total = get_tasks(db_session, assignee.id)

        assert total >= 1
        task_ids = {t.id for t in tasks}
        assert task.id in task_ids

    def test_get_tasks_with_title_filter(self, db_session: Session):
        """Test filtering tasks by title"""
        creator = UserFactory.create(db_session)
        important_title = "Important task title"
        task1 = TaskFactory.create(db_session, creator, title=important_title)
        task2 = TaskFactory.create(db_session, creator, title=fake.sentence(nb_words=2))

        tasks, total = get_tasks(db_session, creator.id, title="Important")

        assert len(tasks) >= 1
        assert any(t.id == task1.id for t in tasks)

    def test_get_tasks_with_status_filter(self, db_session: Session):
        """Test filtering tasks by status"""
        creator = UserFactory.create(db_session)
        task1 = TaskFactory.create(db_session, creator, status="todo")
        task2 = TaskFactory.create(db_session, creator, status="in_progress")

        tasks, total = get_tasks(db_session, creator.id, status="todo")

        assert len(tasks) >= 1
        assert all(t.status == "todo" for t in tasks)

    def test_get_tasks_pagination(self, db_session: Session):
        """Test task pagination"""
        creator = UserFactory.create(db_session)
        for i in range(5):
            TaskFactory.create(db_session, creator, title=fake.sentence(nb_words=2))

        tasks_page1, total1 = get_tasks(db_session, creator.id, page=1, limit=2)
        tasks_page2, total2 = get_tasks(db_session, creator.id, page=2, limit=2)

        assert len(tasks_page1) == 2
        assert len(tasks_page2) == 2
        assert total1 == total2
        # Ensure different tasks on different pages
        page1_ids = {t.id for t in tasks_page1}
        page2_ids = {t.id for t in tasks_page2}
        assert len(page1_ids & page2_ids) == 0

    def test_get_tasks_access_control(self, db_session: Session):
        """Test that users only see tasks they have access to"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator)

        tasks, total = get_tasks(db_session, other_user.id)

        task_ids = {t.id for t in tasks}
        assert task.id not in task_ids


class TestGetTask:
    """Tests for get_task function"""

    def test_get_task_success(self, db_session: Session):
        """Test retrieving a task"""
        creator = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator)

        retrieved_task = get_task(db_session, task.id, creator.id)

        assert retrieved_task is not None
        assert retrieved_task.id == task.id
        assert retrieved_task.title == task.title

    def test_get_task_no_access(self, db_session: Session):
        """Test retrieving a task without access returns None"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator)

        retrieved_task = get_task(db_session, task.id, other_user.id)

        assert retrieved_task is None

    def test_get_task_nonexistent(self, db_session: Session):
        """Test retrieving a nonexistent task returns None"""
        creator = UserFactory.create(db_session)
        fake_task_id = uuid.uuid4()

        retrieved_task = get_task(db_session, fake_task_id, creator.id)

        assert retrieved_task is None


class TestCheckTaskAccess:
    """Tests for check_task_access function"""

    def test_check_task_access_creator(self, db_session: Session):
        """Test creator has access to task"""
        creator = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator)

        has_access = check_task_access(db_session, task.id, creator.id)

        assert has_access is True

    def test_check_task_access_assignee(self, db_session: Session):
        """Test assignee has access to task"""
        creator = UserFactory.create(db_session)
        assignee = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator, assignee=assignee)

        has_access = check_task_access(db_session, task.id, assignee.id)

        assert has_access is True

    def test_check_task_access_project_member(self, db_session: Session):
        """Test project member has access to task"""
        creator = UserFactory.create(db_session)
        member = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)
        task = TaskFactory.create(db_session, creator)
        TaskProjectFactory.create(db_session, task, project)

        # Add member to project
        from app.services.project import add_user_to_project

        add_user_to_project(db_session, project.id, member.id, "member")

        has_access = check_task_access(db_session, task.id, member.id)

        assert has_access is True

    def test_check_task_access_no_access(self, db_session: Session):
        """Test user without access cannot access task"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        task = TaskFactory.create(db_session, creator)

        has_access = check_task_access(db_session, task.id, other_user.id)

        assert has_access is False

    def test_check_task_access_nonexistent_task(self, db_session: Session):
        """Test checking access to nonexistent task returns False"""
        creator = UserFactory.create(db_session)
        fake_task_id = uuid.uuid4()

        has_access = check_task_access(db_session, fake_task_id, creator.id)

        assert has_access is False


class TestBulkCreateTasks:
    """Tests for bulk_create_tasks function"""

    def test_bulk_create_tasks_success(self, db_session: Session):
        """Test creating multiple tasks"""
        creator = UserFactory.create(db_session)
        project = ProjectFactory.create(db_session, creator)

        tasks_data = [
            TaskCreate(title=fake.sentence(nb_words=2), project_ids=[project.id]),
            TaskCreate(title=fake.sentence(nb_words=2), project_ids=[project.id]),
            TaskCreate(title=fake.sentence(nb_words=2), project_ids=[project.id]),
        ]

        results = bulk_create_tasks(db_session, tasks_data, creator.id)

        assert len(results) == 3
        assert all(r["success"] for r in results)
        assert all("id" in r for r in results)

    def test_bulk_create_tasks_partial_failure(self, db_session: Session):
        """Test bulk create with some failures"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        project1 = ProjectFactory.create(db_session, creator)
        project2 = ProjectFactory.create(db_session, other_user)

        tasks_data = [
            TaskCreate(title="Task 1", project_ids=[project1.id]),
            TaskCreate(title="Task 2", project_ids=[project2.id]),  # No access
        ]

        results = bulk_create_tasks(db_session, tasks_data, creator.id)

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False


class TestBulkUpdateTasks:
    """Tests for bulk_update_tasks function"""

    def test_bulk_update_tasks_success(self, db_session: Session):
        """Test updating multiple tasks"""
        creator = UserFactory.create(db_session)
        task1 = TaskFactory.create(db_session, creator, title=fake.sentence(nb_words=2))
        task2 = TaskFactory.create(db_session, creator, title=fake.sentence(nb_words=2))

        updates_data = [
            {"id": task1.id, "updates": TaskUpdate(title=fake.sentence(nb_words=2))},
            {"id": task2.id, "updates": TaskUpdate(title=fake.sentence(nb_words=2))},
        ]

        results = bulk_update_tasks(db_session, updates_data, creator.id)

        assert len(results) == 2
        assert all(r["success"] for r in results)

    def test_bulk_update_tasks_partial_failure(self, db_session: Session):
        """Test bulk update with some failures"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        task1 = TaskFactory.create(db_session, creator)
        task2 = TaskFactory.create(db_session, other_user)

        updates_data = [
            {"id": task1.id, "updates": TaskUpdate(title=fake.sentence(nb_words=2))},
            {"id": task2.id, "updates": TaskUpdate(title=fake.sentence(nb_words=2))},  # No access
        ]

        results = bulk_update_tasks(db_session, updates_data, creator.id)

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False


class TestBulkDeleteTasks:
    """Tests for bulk_delete_tasks function"""

    def test_bulk_delete_tasks_success(self, db_session: Session):
        """Test deleting multiple tasks"""
        creator = UserFactory.create(db_session)
        task1 = TaskFactory.create(db_session, creator)
        task2 = TaskFactory.create(db_session, creator)

        results = bulk_delete_tasks(db_session, [task1.id, task2.id], creator.id)

        assert len(results) == 2
        assert all(r["success"] for r in results)

    def test_bulk_delete_tasks_partial_failure(self, db_session: Session):
        """Test bulk delete with some failures"""
        creator = UserFactory.create(db_session)
        other_user = UserFactory.create(db_session)
        task1 = TaskFactory.create(db_session, creator)
        task2 = TaskFactory.create(db_session, other_user)

        results = bulk_delete_tasks(db_session, [task1.id, task2.id], creator.id)

        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
