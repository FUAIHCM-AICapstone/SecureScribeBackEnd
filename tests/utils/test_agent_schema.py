"""Unit tests for meeting agent schema models"""

import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker

from app.utils.meeting_agent.agent_schema import (
    InformativeCheckResult,
    MeetingNoteResult,
    MeetingOutput,
    MeetingTypeResult,
    Task,
    TaskItems,
)

fake = Faker()


class TestTaskModel:
    """Tests for Task model"""

    def test_task_creation_minimal(self):
        """Test creating a task with minimal fields"""
        task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
        )

        assert task.title is not None
        assert task.description is not None
        assert task.status == "todo"
        assert task.priority == "Trung bình"
        assert task.creator_id is None
        assert task.assignee_id is None
        assert task.due_date is None
        assert task.project_ids == []

    def test_task_creation_full(self):
        """Test creating a task with all fields"""
        creator_id = uuid.uuid4()
        assignee_id = uuid.uuid4()
        project_id = uuid.uuid4()
        due_date = datetime.now(timezone.utc) + timedelta(days=3)

        task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
            creator_id=creator_id,
            assignee_id=assignee_id,
            status="in_progress",
            priority="Cao",
            due_date=due_date,
            project_ids=[project_id],
            notes=fake.text(),
        )

        assert task.creator_id == creator_id
        assert task.assignee_id == assignee_id
        assert task.status == "in_progress"
        assert task.priority == "Cao"
        assert task.due_date == due_date
        assert project_id in task.project_ids

    def test_task_parse_due_date_string(self):
        """Test task parses due_date string to datetime"""
        task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
            due_date="3 days",
        )

        assert isinstance(task.due_date, datetime)
        assert task.due_date is not None

    def test_task_parse_due_date_none(self):
        """Test task handles null due_date"""
        task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
            due_date="null",
        )

        assert task.due_date is None

    def test_task_parse_due_date_datetime(self):
        """Test task accepts datetime due_date"""
        now = datetime.now(timezone.utc)
        task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
            due_date=now,
        )

        assert task.due_date == now

    def test_task_default_status(self):
        """Test task default status is 'todo'"""
        task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
        )

        assert task.status == "todo"

    def test_task_default_priority(self):
        """Test task default priority is 'Trung bình'"""
        task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
        )

        assert task.priority == "Trung bình"

    def test_task_priority_levels(self):
        """Test all priority levels"""
        priorities = ["Cao", "Trung bình", "Thấp"]

        for priority in priorities:
            task = Task(
                title=fake.sentence(),
                description=fake.paragraph(),
                priority=priority,
            )
            assert task.priority == priority

    def test_task_status_levels(self):
        """Test all status levels"""
        statuses = ["todo", "in_progress", "completed"]

        for status in statuses:
            task = Task(
                title=fake.sentence(),
                description=fake.paragraph(),
                status=status,
            )
            assert task.status == status

    def test_task_multiple_projects(self):
        """Test task with multiple project IDs"""
        project_ids = [uuid.uuid4() for _ in range(3)]
        task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
            project_ids=project_ids,
        )

        assert len(task.project_ids) == 3
        assert all(pid in task.project_ids for pid in project_ids)

    def test_task_notes_field(self):
        """Test task notes field"""
        notes = fake.text()
        task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
            notes=notes,
        )

        assert task.notes == notes


class TestMeetingTypeResult:
    """Tests for MeetingTypeResult model"""

    def test_meeting_type_result_creation(self):
        """Test creating MeetingTypeResult"""
        result = MeetingTypeResult(
            meeting_type="planning",
            reasoning="Cuộc họp tập trung vào lập kế hoạch",
        )

        assert result.meeting_type == "planning"
        assert result.reasoning is not None

    def test_meeting_type_result_no_reasoning(self):
        """Test MeetingTypeResult without reasoning"""
        result = MeetingTypeResult(meeting_type="standup")

        assert result.meeting_type == "standup"
        assert result.reasoning is None

    def test_meeting_type_result_types(self):
        """Test various meeting types"""
        meeting_types = ["planning", "standup", "review", "retrospective", "general"]

        for meeting_type in meeting_types:
            result = MeetingTypeResult(meeting_type=meeting_type)
            assert result.meeting_type == meeting_type


class TestInformativeCheckResult:
    """Tests for InformativeCheckResult model"""

    def test_informative_check_true(self):
        """Test informative check result - true"""
        result = InformativeCheckResult(
            is_informative=True,
            reason="Transcript has substantial content",
        )

        assert result.is_informative is True
        assert result.reason is not None

    def test_informative_check_false(self):
        """Test informative check result - false"""
        result = InformativeCheckResult(
            is_informative=False,
            reason="Transcript is too short",
        )

        assert result.is_informative is False
        assert result.reason is not None

    def test_informative_check_no_reason(self):
        """Test informative check without reason"""
        result = InformativeCheckResult(is_informative=True)

        assert result.is_informative is True
        assert result.reason is None


class TestTaskItems:
    """Tests for TaskItems model"""

    def test_task_items_empty(self):
        """Test TaskItems with no tasks"""
        items = TaskItems()

        assert isinstance(items.tasks, list)
        assert len(items.tasks) == 0

    def test_task_items_single_task(self):
        """Test TaskItems with one task"""
        task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
        )
        items = TaskItems(tasks=[task])

        assert len(items.tasks) == 1
        assert items.tasks[0] == task

    def test_task_items_multiple_tasks(self):
        """Test TaskItems with multiple tasks"""
        tasks = [Task(title=fake.sentence(), description=fake.paragraph()) for _ in range(5)]
        items = TaskItems(tasks=tasks)

        assert len(items.tasks) == 5
        assert all(task in items.tasks for task in tasks)

    def test_task_items_default_empty(self):
        """Test TaskItems default is empty list"""
        items = TaskItems()

        assert items.tasks == []


class TestMeetingNoteResult:
    """Tests for MeetingNoteResult model"""

    def test_meeting_note_result_creation(self):
        """Test creating MeetingNoteResult"""
        note = "# Ghi chú cuộc họp\n\n## Nội dung chính\n- Điểm 1\n- Điểm 2"
        result = MeetingNoteResult(meeting_note=note)

        assert result.meeting_note == note
        assert "# Ghi chú" in result.meeting_note

    def test_meeting_note_result_markdown_format(self):
        """Test MeetingNoteResult contains markdown"""
        note = "# Title\n## Subtitle\n- Item 1\n- Item 2"
        result = MeetingNoteResult(meeting_note=note)

        assert "# Title" in result.meeting_note
        assert "## Subtitle" in result.meeting_note

    def test_meeting_note_result_empty(self):
        """Test MeetingNoteResult with empty note"""
        result = MeetingNoteResult(meeting_note="")

        assert result.meeting_note == ""


class TestMeetingOutput:
    """Tests for MeetingOutput model"""

    def test_meeting_output_full(self):
        """Test creating full MeetingOutput"""
        note = fake.paragraph()
        tasks = [Task(title=fake.sentence(), description=fake.paragraph()) for _ in range(3)]

        output = MeetingOutput(
            meeting_note=note,
            task_items=tasks,
            is_informative=True,
            meeting_type="general",
        )

        assert output.meeting_note == note
        assert len(output.task_items) == 3
        assert output.is_informative is True
        assert output.meeting_type == "general"

    def test_meeting_output_no_tasks(self):
        """Test MeetingOutput with no tasks"""
        output = MeetingOutput(
            meeting_note=fake.paragraph(),
            is_informative=True,
            meeting_type="standup",
        )

        assert len(output.task_items) == 0

    def test_meeting_output_not_informative(self):
        """Test MeetingOutput with is_informative false"""
        output = MeetingOutput(
            meeting_note="Short note",
            is_informative=False,
            meeting_type="general",
        )

        assert output.is_informative is False

    def test_meeting_output_all_meeting_types(self):
        """Test MeetingOutput with various meeting types"""
        meeting_types = ["planning", "standup", "review", "retrospective", "general"]

        for meeting_type in meeting_types:
            output = MeetingOutput(
                meeting_note=fake.paragraph(),
                is_informative=True,
                meeting_type=meeting_type,
            )
            assert output.meeting_type == meeting_type


class TestMeetingStateTypedDict:
    """Tests for MeetingState TypedDict"""

    def test_meeting_state_creation(self):
        """Test creating MeetingState"""
        from app.utils.meeting_agent.agent_schema import MeetingState

        state: MeetingState = {
            "messages": [{"role": "user", "content": "test"}],
            "transcript": fake.paragraph(),
            "meeting_note": fake.paragraph(),
            "task_items": [],
            "is_informative": True,
            "meeting_type": "general",
        }

        assert state["messages"] is not None
        assert state["transcript"] is not None
        assert state["is_informative"] is True

    def test_meeting_state_partial(self):
        """Test MeetingState with partial fields"""
        from app.utils.meeting_agent.agent_schema import MeetingState

        state: MeetingState = {
            "transcript": fake.paragraph(),
            "meeting_type": "planning",
        }

        assert "transcript" in state
        assert "meeting_type" in state
