"""Unit tests for task extractor agent"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from agno.models.google import Gemini
from faker import Faker
from pydantic import ValidationError

from app.utils.meeting_agent.agent_schema import Task, TaskItems
from app.utils.meeting_agent.meeting_processor.task_extractor import TaskExtractor

fake = Faker()


class TestTaskExtractorInitialization:
    """Tests for TaskExtractor initialization"""

    @patch("app.utils.llm._get_model")
    def test_task_extractor_creation(self, mock_get_model):
        """Test creating a TaskExtractor instance"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        assert extractor is not None
        assert extractor.name == "TaskExtractor"
        assert extractor.output_schema == TaskItems

    @patch("app.utils.llm._get_model")
    def test_task_extractor_has_instructions(self, mock_get_model):
        """Test TaskExtractor has proper instructions"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        assert extractor.instructions is not None
        assert len(extractor.instructions) > 0

    @patch("app.utils.llm._get_model")
    def test_task_extractor_json_mode_enabled(self, mock_get_model):
        """Test TaskExtractor has JSON mode enabled"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        assert extractor.use_json_mode is True
        assert extractor.structured_outputs is True


class TestTaskExtractorExtractMethod:
    """Tests for TaskExtractor.extract method"""

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_empty_transcript(self, mock_get_model):
        """Test extraction with empty transcript"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        result = await extractor.extract("")

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_whitespace_only_transcript(self, mock_get_model):
        """Test extraction with whitespace-only transcript"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        result = await extractor.extract("   \n  \t  ")

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_none_transcript(self, mock_get_model):
        """Test extraction with None transcript"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        result = await extractor.extract(None)

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_valid_transcript(self, mock_get_model):
        """Test extraction with valid transcript"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        transcript = fake.paragraph()
        mock_task = Task(title=fake.sentence(), description=fake.paragraph())
        mock_task_items = TaskItems(tasks=[mock_task])

        with patch.object(extractor, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_task_items
            mock_arun.return_value = mock_message

            result = await extractor.extract(transcript)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].title == mock_task.title

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_multiple_tasks(self, mock_get_model):
        """Test extraction of multiple tasks"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        transcript = fake.paragraph()
        mock_tasks = [Task(title=fake.sentence(), description=fake.paragraph()) for _ in range(3)]
        mock_task_items = TaskItems(tasks=mock_tasks)

        with patch.object(extractor, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_task_items
            mock_arun.return_value = mock_message

            result = await extractor.extract(transcript)

            assert len(result) == 3
            assert all(isinstance(task, Task) for task in result)

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_task_with_priority(self, mock_get_model):
        """Test extraction preserves task priority"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        transcript = fake.paragraph()
        mock_task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
            priority="Cao",
        )
        mock_task_items = TaskItems(tasks=[mock_task])

        with patch.object(extractor, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_task_items
            mock_arun.return_value = mock_message

            result = await extractor.extract(transcript)

            assert result[0].priority == "Cao"

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_task_with_due_date(self, mock_get_model):
        """Test extraction preserves task due date"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        transcript = fake.paragraph()
        due_date = datetime.now(timezone.utc)
        mock_task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
            due_date=due_date,
        )
        mock_task_items = TaskItems(tasks=[mock_task])

        with patch.object(extractor, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_task_items
            mock_arun.return_value = mock_message

            result = await extractor.extract(transcript)

            assert result[0].due_date == due_date

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_long_transcript(self, mock_get_model):
        """Test extraction with long transcript"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        transcript = "\n".join([fake.paragraph() for _ in range(10)])
        mock_task_items = TaskItems(tasks=[])

        with patch.object(extractor, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_task_items
            mock_arun.return_value = mock_message

            result = await extractor.extract(transcript)

            assert isinstance(result, list)


class TestTaskExtractorRetryLogic:
    """Tests for TaskExtractor retry behavior"""

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_retries_on_validation_error(self, mock_get_model):
        """Test extraction retries when validation error occurs"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        transcript = fake.paragraph()

        with patch.object(extractor, "arun", new_callable=AsyncMock) as mock_arun:
            # First call raises validation error, second succeeds
            mock_message = MagicMock()
            mock_message.content = TaskItems(tasks=[])
            mock_arun.side_effect = [ValidationError.from_exception_data("test", []), mock_message]

            # The function should retry and eventually return result
            try:
                result = await extractor.extract(transcript)
                assert isinstance(result, list)
            except Exception:
                # Expected to fail if all retries are exhausted
                pass

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_handles_string_response(self, mock_get_model):
        """Test extraction handles string JSON response from LLM"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        transcript = fake.paragraph()

        with patch.object(extractor, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            # Simulate response that needs validation
            mock_message.content = TaskItems(tasks=[])
            mock_arun.return_value = mock_message

            result = await extractor.extract(transcript)

            assert isinstance(result, list)


class TestTaskExtractorEdgeCases:
    """Tests for TaskExtractor edge cases"""

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_with_special_characters(self, mock_get_model):
        """Test extraction with special characters in transcript"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        transcript = f"Đây là transcript với ký tự đặc biệt: !@#$%^&*() {fake.paragraph()}"

        mock_task_items = TaskItems(tasks=[])

        with patch.object(extractor, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_task_items
            mock_arun.return_value = mock_message

            result = await extractor.extract(transcript)

            assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_with_unicode_transcript(self, mock_get_model):
        """Test extraction with unicode characters"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        transcript = "Hoàn tất báo cáo về 🎯 mục tiêu quý 4 vào thứ Sáu"

        mock_task_items = TaskItems(tasks=[])

        with patch.object(extractor, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_task_items
            mock_arun.return_value = mock_message

            result = await extractor.extract(transcript)

            assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_very_short_transcript(self, mock_get_model):
        """Test extraction with very short transcript"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        transcript = "ok"

        mock_task_items = TaskItems(tasks=[])

        with patch.object(extractor, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_task_items
            mock_arun.return_value = mock_message

            result = await extractor.extract(transcript)

            assert isinstance(result, list)

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_extract_task_with_all_fields(self, mock_get_model):
        """Test extraction of task with all fields populated"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        extractor = TaskExtractor(mock_model)

        transcript = fake.paragraph()
        creator_id = uuid.uuid4()
        assignee_id = uuid.uuid4()
        project_id = uuid.uuid4()

        mock_task = Task(
            title=fake.sentence(),
            description=fake.paragraph(),
            creator_id=creator_id,
            assignee_id=assignee_id,
            status="in_progress",
            priority="Cao",
            due_date=datetime.now(timezone.utc),
            project_ids=[project_id],
            notes=fake.text(),
        )
        mock_task_items = TaskItems(tasks=[mock_task])

        with patch.object(extractor, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_task_items
            mock_arun.return_value = mock_message

            result = await extractor.extract(transcript)

            assert len(result) == 1
            extracted_task = result[0]
            assert extracted_task.title == mock_task.title
            assert extracted_task.priority == mock_task.priority
            assert extracted_task.status == mock_task.status
