from __future__ import annotations

import asyncio
from typing import Any, Dict, Iterable, List, Optional

from app.utils.meeting_agent.agent_schema import MeetingOutput, Task

from .note_generator import NoteGenerator
from .task_extractor import TaskExtractor

__all__ = ["MeetingProcessor"]


class MeetingProcessor:
    """Co-ordinate meeting processing with concurrent execution."""

    def __init__(self, model: Any) -> None:
        self._model = model
        self._task_extractor = TaskExtractor(self._model)
        self._note_generator = NoteGenerator(self._model)

    async def process_meeting(self, transcript: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Process meeting transcript with concurrent task extraction and note generation.

        Args:
            transcript: Meeting transcript text
            custom_prompt: Optional custom prompt for note generation

        Returns:
            Dictionary containing meeting_note, task_items, is_informative, meeting_type
        """
        transcript_value = transcript or ""

        print(f"[MeetingProcessor] Starting meeting processing - transcript_length: {len(transcript_value)}")

        # Step 1: Simple validation
        if not self._simple_validation(transcript_value):
            print("[MeetingProcessor] Validation failed, returning empty result")
            return self._format_failure("Transcript validation failed: too short or empty")

        # Step 2: Concurrent extraction with error handling
        try:
            print("[MeetingProcessor] Starting concurrent extraction (tasks + note)")
            results = await asyncio.gather(
                self._extract_tasks_with_retry(transcript_value),
                self._generate_note_with_retry(transcript_value, custom_prompt),
                return_exceptions=True,  # Continue even if one fails
            )

            tasks_result = results[0]
            note_result = results[1]

            # Handle partial failures
            if isinstance(tasks_result, Exception):
                print(f"[MeetingProcessor] Task extraction failed: {tasks_result}")
                tasks_result = []  # Empty list as fallback

            if isinstance(note_result, Exception):
                print(f"[MeetingProcessor] Note generation failed: {note_result}")
                note_result = "Không thể tạo ghi chú cuộc họp do lỗi xử lý."  # Fallback message

            print(f"[MeetingProcessor] Concurrent extraction completed - tasks: {len(tasks_result) if isinstance(tasks_result, list) else 0}, note_length: {len(note_result) if isinstance(note_result, str) else 0}")

        except Exception as exc:
            print(f"[MeetingProcessor] Concurrent execution failed completely: {exc}")
            return self._format_failure(str(exc))

        # Step 3: Format and return success
        return self._format_success(tasks_result, note_result)

    def _simple_validation(self, transcript: str) -> bool:
        """
        Simple validation without LLM call.

        Args:
            transcript: Transcript text to validate

        Returns:
            True if valid, False otherwise
        """
        if not transcript or not transcript.strip():
            print("[MeetingProcessor] Validation: transcript is empty")
            return False

        if len(transcript.strip()) < 100:
            print(f"[MeetingProcessor] Validation: transcript too short ({len(transcript.strip())} < 100 chars)")
            return False

        print(f"[MeetingProcessor] Validation: passed ({len(transcript.strip())} chars)")
        return True

    async def _extract_tasks_with_retry(self, transcript: str) -> List[Task]:
        """
        Extract tasks with built-in retry logic.

        Args:
            transcript: Meeting transcript

        Returns:
            List of extracted tasks (empty list on failure after retries)
        """
        try:
            print("[MeetingProcessor] Calling task extractor...")
            tasks = await self._task_extractor.extract(transcript)
            print(f"[MeetingProcessor] Task extraction successful: {len(tasks)} tasks")
            return tasks
        except Exception as exc:
            print(f"[MeetingProcessor] Task extraction failed after retries: {exc}")
            return []  # Return empty list as fallback

    async def _generate_note_with_retry(self, transcript: str, custom_prompt: Optional[str] = None) -> str:
        """
        Generate meeting note with built-in retry logic.

        Args:
            transcript: Meeting transcript
            custom_prompt: Optional custom prompt

        Returns:
            Generated meeting note (fallback message on failure after retries)
        """
        try:
            print("[MeetingProcessor] Calling note generator...")
            # Pass empty task list for now, will be updated after concurrent execution
            note = await self._note_generator.generate(transcript, [], custom_prompt)
            print(f"[MeetingProcessor] Note generation successful: {len(note)} chars")
            return note
        except Exception as exc:
            print(f"[MeetingProcessor] Note generation failed after retries: {exc}")
            return "Không thể tạo ghi chú cuộc họp do lỗi xử lý."  # Fallback message

    def _format_success(self, tasks: List[Task], note: str) -> Dict[str, Any]:
        """
        Format successful processing result.

        Args:
            tasks: List of extracted tasks
            note: Generated meeting note

        Returns:
            Formatted result dictionary
        """
        # Ensure tasks is a list
        if not isinstance(tasks, list):
            tasks = []

        # Convert Task objects to dicts
        tasks_list = self._ensure_model_list(tasks, Task)

        output = MeetingOutput(
            meeting_note=note if isinstance(note, str) else "",
            task_items=tasks_list,
            is_informative=True,  # Always true if we got here
            meeting_type="general",  # Always general
        )

        result = output.model_dump()
        result["task_items"] = [task.model_dump() for task in output.task_items]

        print(f"[MeetingProcessor] Success result formatted - tasks: {len(result['task_items'])}, note_length: {len(result['meeting_note'])}")

        return result

    def _format_failure(self, message: str) -> Dict[str, Any]:
        """
        Format failure result.

        Args:
            message: Error message

        Returns:
            Formatted failure dictionary
        """
        print(f"[MeetingProcessor] Returning fallback response: {message}")
        return {
            "meeting_note": "",
            "task_items": [],
            "is_informative": False,
            "meeting_type": "general",
        }

    @staticmethod
    def _ensure_model_list(items: Iterable[Any], model_cls: Any) -> list:
        """
        Ensure all items are instances of the model class.

        Args:
            items: Iterable of items
            model_cls: Model class to convert to

        Returns:
            List of model instances
        """
        converted = []
        for item in items:
            if isinstance(item, model_cls):
                converted.append(item)
            elif isinstance(item, dict):
                try:
                    converted.append(model_cls(**item))
                except Exception as exc:
                    print(f"[MeetingProcessor] Failed to convert item to {model_cls.__name__}: {exc}")
        return converted
