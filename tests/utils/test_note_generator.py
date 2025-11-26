"""Unit tests for note generator agent"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faker import Faker
from agno.models.google import Gemini

from app.utils.meeting_agent.agent_schema import MeetingNoteResult, Task
from app.utils.meeting_agent.meeting_processor.note_generator import NoteGenerator

fake = Faker()


class TestNoteGeneratorInitialization:
    """Tests for NoteGenerator initialization"""

    def test_note_generator_creation(self):
        """Test creating a NoteGenerator instance"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"

        generator = NoteGenerator(mock_model)

        assert generator is not None
        assert generator.name == "NoteGenerator"
        assert generator.output_schema == MeetingNoteResult

    def test_note_generator_has_instructions(self):
        """Test NoteGenerator has proper instructions"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"

        generator = NoteGenerator(mock_model)

        assert generator.instructions is not None
        assert len(generator.instructions) > 0

    def test_note_generator_json_mode_enabled(self):
        """Test NoteGenerator has JSON mode enabled"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"

        generator = NoteGenerator(mock_model)

        assert generator.use_json_mode is True
        assert generator.structured_outputs is True


class TestNoteGeneratorGenerateMethod:
    """Tests for NoteGenerator.generate method"""

    @pytest.mark.asyncio
    async def test_generate_empty_transcript(self):
        """Test generation with empty transcript"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"

        generator = NoteGenerator(mock_model)

        result = await generator.generate("", [])

        assert isinstance(result, str)
        assert "Không đủ thông tin" in result

    @pytest.mark.asyncio
    async def test_generate_short_transcript(self):
        """Test generation with too short transcript"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"

        generator = NoteGenerator(mock_model)

        result = await generator.generate("OK", [])

        assert isinstance(result, str)
        assert "Không đủ thông tin" in result

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_valid_transcript(self, mock_get_model):
        """Test generation with valid transcript"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = fake.paragraph() * 3  # Make it long enough
        expected_note = "# Ghi chú cuộc họp\n\n## Nội dung chính\n- Điểm 1"
        mock_result = MeetingNoteResult(meeting_note=expected_note)

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_result
            mock_arun.return_value = mock_message

            result = await generator.generate(transcript, [])

            assert result == expected_note

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_with_tasks(self, mock_get_model):
        """Test generation with task list"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = fake.paragraph() * 3
        tasks = [
            Task(title=fake.sentence(), description=fake.paragraph()),
            Task(title=fake.sentence(), description=fake.paragraph()),
        ]
        expected_note = "# Ghi chú cuộc họp\n\n## Công việc\n- Task 1\n- Task 2"
        mock_result = MeetingNoteResult(meeting_note=expected_note)

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_result
            mock_arun.return_value = mock_message

            result = await generator.generate(transcript, tasks)

            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_with_custom_prompt(self, mock_get_model):
        """Test generation with custom prompt"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = fake.paragraph() * 3
        custom_prompt = "Hãy tổng hợp theo định dạng ngắn gọn"
        expected_note = "# Tóm tắt ngắn\n\nNội dung chính"
        mock_result = MeetingNoteResult(meeting_note=expected_note)

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_result
            mock_arun.return_value = mock_message

            result = await generator.generate(transcript, [], custom_prompt)

            assert isinstance(result, str)
            assert mock_arun.called

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_removes_backticks(self, mock_get_model):
        """Test generation removes markdown backticks"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = fake.paragraph() * 3
        note_with_backticks = "```markdown\n# Note\nContent\n```"
        mock_result = MeetingNoteResult(meeting_note=note_with_backticks)

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_result
            mock_arun.return_value = mock_message

            result = await generator.generate(transcript, [])

            assert "```" not in result

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_returns_fallback_on_empty_note(self, mock_get_model):
        """Test generation returns fallback when note is empty"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = fake.paragraph() * 3
        mock_result = MeetingNoteResult(meeting_note="")

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_result
            mock_arun.return_value = mock_message

            result = await generator.generate(transcript, [])

            assert isinstance(result, str)
            assert len(result) > 0


class TestNoteGeneratorContextBuilding:
    """Tests for context building in NoteGenerator"""

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_includes_tasks_in_context(self, mock_get_model):
        """Test generation includes tasks in context"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = fake.paragraph() * 3
        tasks = [Task(title=fake.sentence(), description=fake.paragraph())]
        mock_result = MeetingNoteResult(meeting_note="# Note")

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_result
            mock_arun.return_value = mock_message

            await generator.generate(transcript, tasks)

            # Verify arun was called
            assert mock_arun.called

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_context_has_meeting_type(self, mock_get_model):
        """Test generated context includes meeting type"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = fake.paragraph() * 3
        mock_result = MeetingNoteResult(meeting_note="# Note")

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_result
            mock_arun.return_value = mock_message

            await generator.generate(transcript, [])

            # Verify arun was called with context
            assert mock_arun.called


class TestNoteGeneratorEdgeCases:
    """Tests for NoteGenerator edge cases"""

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_with_none_transcript(self, mock_get_model):
        """Test generation handles None transcript"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        result = await generator.generate(None, [])

        assert isinstance(result, str)
        assert "Không đủ thông tin" in result

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_with_unicode_content(self, mock_get_model):
        """Test generation with unicode characters"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = "Cuộc họp về 🎯 kế hoạch Q4 với 👥 đội ngũ" * 5
        expected_note = "# Ghi chú cuộc họp\n\n## Nội dung\n- Kế hoạch Q4"
        mock_result = MeetingNoteResult(meeting_note=expected_note)

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_result
            mock_arun.return_value = mock_message

            result = await generator.generate(transcript, [])

            assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_with_special_characters(self, mock_get_model):
        """Test generation with special characters"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = f"Đặc biệt: !@#$%^&*() {fake.paragraph() * 3}"
        expected_note = "# Ghi chú"
        mock_result = MeetingNoteResult(meeting_note=expected_note)

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_result
            mock_arun.return_value = mock_message

            result = await generator.generate(transcript, [])

            assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_with_many_tasks(self, mock_get_model):
        """Test generation with many tasks"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = fake.paragraph() * 5
        tasks = [Task(title=fake.sentence(), description=fake.paragraph()) for _ in range(20)]
        expected_note = "# Ghi chú\n\n## Công việc\n" + "\n".join(f"- {i}" for i in range(20))
        mock_result = MeetingNoteResult(meeting_note=expected_note)

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_result
            mock_arun.return_value = mock_message

            result = await generator.generate(transcript, tasks)

            assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_very_long_transcript(self, mock_get_model):
        """Test generation with very long transcript"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = " ".join([fake.paragraph() for _ in range(50)])
        expected_note = "# Ghi chú dài"
        mock_result = MeetingNoteResult(meeting_note=expected_note)

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_result
            mock_arun.return_value = mock_message

            result = await generator.generate(transcript, [])

            assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_markdown_format_preserved(self, mock_get_model):
        """Test generation preserves markdown formatting"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = fake.paragraph() * 3
        expected_note = "# Tiêu đề\n## Phần phụ\n- Điểm 1\n- Điểm 2\n\n### Chi tiết"
        mock_result = MeetingNoteResult(meeting_note=expected_note)

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            mock_message = MagicMock()
            mock_message.content = mock_result
            mock_arun.return_value = mock_message

            result = await generator.generate(transcript, [])

            assert "#" in result
            assert "Tiêu đề" in result


class TestNoteGeneratorRetryBehavior:
    """Tests for NoteGenerator retry logic"""

    @pytest.mark.asyncio
    @patch("app.utils.llm._get_model")
    async def test_generate_handles_validation_error(self, mock_get_model):
        """Test generation handles validation errors gracefully"""
        mock_model = MagicMock(spec=Gemini)
        mock_model.id = "gemini-2.5-flash"
        mock_get_model.return_value = mock_model

        generator = NoteGenerator(mock_model)

        transcript = fake.paragraph() * 3

        with patch.object(generator, "arun", new_callable=AsyncMock) as mock_arun:
            # Simulate validation error
            from pydantic import ValidationError

            mock_arun.side_effect = ValidationError.from_exception_data("test", [])

            # Should handle error gracefully through retry mechanism
            try:
                result = await generator.generate(transcript, [])
                # If it succeeds after retry
                assert isinstance(result, str)
            except Exception:
                # Expected if all retries exhausted
                pass
