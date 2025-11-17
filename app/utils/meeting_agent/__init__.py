from __future__ import annotations

from typing import Optional

from agno.models.google import Gemini

from app.utils.llm import _get_model

from .meeting_processor import MeetingProcessor

__all__ = ["MeetingAnalyzer"]


class MeetingAnalyzer:
    """Facade that coordinates meeting analysis for SecureScribe."""

    def __init__(self) -> None:
        self._processor = self._create_processor()

    async def complete(
        self,
        transcript: Optional[str],
        custom_prompt: Optional[str] = None,
    ) -> dict:
        """
        Analyze meeting transcript and extract tasks + generate note.

        Args:
            transcript: Meeting transcript text
            custom_prompt: Optional custom prompt for note generation

        Returns:
            Dictionary with meeting_note, task_items, is_informative, meeting_type
        """
        transcript_value = transcript or ""

        print(f"[MeetingAnalyzer] Starting analysis - transcript_length: {len(transcript_value)}")

        try:
            result = await self._processor.process_meeting(transcript_value, custom_prompt=custom_prompt)
            print("[MeetingAnalyzer] Analysis completed successfully")
            return result
        except Exception as exc:
            print(f"[MeetingAnalyzer] Meeting analysis failed: {exc}")
            return {
                "meeting_note": "",
                "task_items": [],
                "is_informative": False,
                "meeting_type": "general",
            }

    def _create_processor(self) -> MeetingProcessor:
        """Create a new MeetingProcessor instance."""
        model = self._instantiate_model()
        return MeetingProcessor(model=model)

    @staticmethod
    def _instantiate_model() -> Gemini:
        """Instantiate the Gemini model for processing."""
        return _get_model()
