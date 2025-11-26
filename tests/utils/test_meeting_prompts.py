"""Unit tests for meeting agent prompts"""

from faker import Faker

from app.utils.meeting_agent.meeting_prompts import (
    GENERAL_MEETING_PROMPT,
    TASK_EXTRACTION_PROMPT_TEMPLATE,
    get_prompt_for_meeting_type,
    get_task_extraction_prompt,
)

fake = Faker()


class TestGeneralMeetingPrompt:
    """Tests for GENERAL_MEETING_PROMPT constant"""

    def test_general_meeting_prompt_exists(self):
        """Test GENERAL_MEETING_PROMPT is defined"""
        assert GENERAL_MEETING_PROMPT is not None
        assert isinstance(GENERAL_MEETING_PROMPT, str)
        assert len(GENERAL_MEETING_PROMPT) > 0

    def test_general_meeting_prompt_vietnamese(self):
        """Test prompt is in Vietnamese"""
        assert "Tóm tắt" in GENERAL_MEETING_PROMPT or "tóm tắt" in GENERAL_MEETING_PROMPT

    def test_general_meeting_prompt_has_structure(self):
        """Test prompt has required structure"""
        assert "##" in GENERAL_MEETING_PROMPT or "#" in GENERAL_MEETING_PROMPT
        assert "cuộc họp" in GENERAL_MEETING_PROMPT.lower()

    def test_general_meeting_prompt_mentions_decisions(self):
        """Test prompt mentions decisions"""
        prompt_lower = GENERAL_MEETING_PROMPT.lower()
        assert "quyết định" in prompt_lower or "decision" in GENERAL_MEETING_PROMPT


class TestTaskExtractionPrompt:
    """Tests for TASK_EXTRACTION_PROMPT_TEMPLATE constant"""

    def test_task_extraction_prompt_exists(self):
        """Test TASK_EXTRACTION_PROMPT_TEMPLATE is defined"""
        assert TASK_EXTRACTION_PROMPT_TEMPLATE is not None
        assert isinstance(TASK_EXTRACTION_PROMPT_TEMPLATE, str)
        assert len(TASK_EXTRACTION_PROMPT_TEMPLATE) > 0

    def test_task_extraction_prompt_vietnamese(self):
        """Test prompt is in Vietnamese"""
        assert "nhiệm vụ" in TASK_EXTRACTION_PROMPT_TEMPLATE.lower()

    def test_task_extraction_prompt_mentions_schema(self):
        """Test prompt mentions schema"""
        prompt_lower = TASK_EXTRACTION_PROMPT_TEMPLATE.lower()
        assert "schema" in prompt_lower or "json" in prompt_lower

    def test_task_extraction_prompt_mentions_deadline(self):
        """Test prompt mentions deadline"""
        prompt_lower = TASK_EXTRACTION_PROMPT_TEMPLATE.lower()
        assert "deadline" in prompt_lower or "thời hạn" in prompt_lower

    def test_task_extraction_prompt_mentions_priority(self):
        """Test prompt mentions priority"""
        prompt_lower = TASK_EXTRACTION_PROMPT_TEMPLATE.lower()
        assert "priority" in prompt_lower or "ưu tiên" in prompt_lower

    def test_task_extraction_prompt_date_formats(self):
        """Test prompt specifies date formats"""
        assert "days" in TASK_EXTRACTION_PROMPT_TEMPLATE.lower()
        assert "weeks" in TASK_EXTRACTION_PROMPT_TEMPLATE.lower()


class TestGetPromptForMeetingType:
    """Tests for get_prompt_for_meeting_type function"""

    def test_get_prompt_for_general_type(self):
        """Test getting prompt for general meeting type"""
        prompt = get_prompt_for_meeting_type("general")

        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_get_prompt_for_planning_type(self):
        """Test getting prompt for planning meeting type"""
        prompt = get_prompt_for_meeting_type("planning")

        assert prompt is not None
        assert isinstance(prompt, str)
        # Currently returns GENERAL_MEETING_PROMPT for all types
        assert prompt == GENERAL_MEETING_PROMPT

    def test_get_prompt_for_standup_type(self):
        """Test getting prompt for standup meeting type"""
        prompt = get_prompt_for_meeting_type("standup")

        assert prompt is not None
        assert isinstance(prompt, str)

    def test_get_prompt_default_type(self):
        """Test getting prompt with default type"""
        prompt = get_prompt_for_meeting_type()

        assert prompt is not None
        assert isinstance(prompt, str)

    def test_get_prompt_returns_general_for_all_types(self):
        """Test function always returns GENERAL_MEETING_PROMPT"""
        types = ["general", "planning", "standup", "review", "retrospective"]

        for meeting_type in types:
            prompt = get_prompt_for_meeting_type(meeting_type)
            assert prompt == GENERAL_MEETING_PROMPT


class TestGetTaskExtractionPrompt:
    """Tests for get_task_extraction_prompt function"""

    def test_get_task_extraction_prompt_returns_string(self):
        """Test get_task_extraction_prompt returns a string"""
        prompt = get_task_extraction_prompt()

        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_get_task_extraction_prompt_is_template(self):
        """Test returned prompt is the template"""
        prompt = get_task_extraction_prompt()

        assert prompt == TASK_EXTRACTION_PROMPT_TEMPLATE

    def test_get_task_extraction_prompt_has_instructions(self):
        """Test prompt contains task extraction instructions"""
        prompt = get_task_extraction_prompt()

        assert "trích xuất" in prompt.lower() or "extract" in prompt.lower()


class TestPromptContent:
    """Tests for prompt content quality and structure"""

    def test_general_prompt_no_english_sensitive_terms(self):
        """Test general prompt doesn't use English sensitive terms inappropriately"""
        # Should be mostly Vietnamese - count actual Vietnamese characters (excluding punctuation)
        vietnamese_chars = sum(1 for char in GENERAL_MEETING_PROMPT if ord(char) > 127 and char not in '.,;:!?()[]{}""')
        total_chars = len(GENERAL_MEETING_PROMPT)
        assert vietnamese_chars > total_chars * 0.15  # At least 15% Vietnamese characters (excluding punctuation)

    def test_task_extraction_prompt_no_repeats(self):
        """Test task extraction prompt doesn't have unnecessary repetition"""
        lines = TASK_EXTRACTION_PROMPT_TEMPLATE.split("\n")
        # Check first 100 lines don't have exact duplicates (ignore empty lines)
        first_100_lines = [line for line in lines[:100] if line.strip()]
        assert len(first_100_lines) == len(set(first_100_lines))

    def test_prompts_have_example_format(self):
        """Test prompts include example formats"""
        general_lower = GENERAL_MEETING_PROMPT.lower()
        extraction_lower = TASK_EXTRACTION_PROMPT_TEMPLATE.lower()

        # Check for markdown or structured examples
        assert "```" in GENERAL_MEETING_PROMPT or "#" in GENERAL_MEETING_PROMPT

    def test_task_prompt_date_formats_documented(self):
        """Test task prompt documents date formats clearly"""
        formats = ["days", "weeks", "end of week", "end of month", "next"]
        prompt_lower = TASK_EXTRACTION_PROMPT_TEMPLATE.lower()

        for format_str in formats:
            assert format_str in prompt_lower


class TestPromptConsistency:
    """Tests for consistency between prompts"""

    def test_prompts_use_same_language(self):
        """Test both prompts use Vietnamese"""
        general_has_vi = "cuộc họp" in GENERAL_MEETING_PROMPT.lower() or "tóm tắt" in GENERAL_MEETING_PROMPT.lower()
        task_has_vi = "nhiệm vụ" in TASK_EXTRACTION_PROMPT_TEMPLATE.lower()

        assert general_has_vi
        assert task_has_vi

    def test_prompts_mention_json_output(self):
        """Test prompts mention JSON output format"""
        general_has_json = "json" in GENERAL_MEETING_PROMPT.lower()
        task_has_json = "json" in TASK_EXTRACTION_PROMPT_TEMPLATE.lower()

        # At least task extraction should mention JSON
        assert task_has_json

    def test_prompts_avoid_ambiguity(self):
        """Test prompts are clear and unambiguous"""
        # Check minimum length for clarity
        assert len(GENERAL_MEETING_PROMPT) > 500
        assert len(TASK_EXTRACTION_PROMPT_TEMPLATE) > 500
