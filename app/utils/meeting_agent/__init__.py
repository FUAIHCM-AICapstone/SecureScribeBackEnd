from __future__ import annotations

import logging
from typing import Optional

from agno.models.google import Gemini

from app.utils.llm import _get_model
from .meeting_processor import MeetingProcessor

LOGGER = logging.getLogger("MeetingAnalyzer")

__all__ = ["MeetingAnalyzer"]


class MeetingAnalyzer:
    """Facade that coordinates meeting analysis for SecureScribe."""

    def __init__(self) -> None:
        self._logger = LOGGER
        self._default_processor = self._create_processor()

    async def complete(
        self,
        transcript: Optional[str],
        meeting_type: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> dict:
        transcript_value = transcript or ""
        processor = self._default_processor
        if meeting_type:
            self._logger.info("Using requested meeting type: %s", meeting_type)
            processor = self._create_processor(meeting_type=meeting_type)
        else:
            self._logger.info("Meeting type not specified; detector will infer it")

        try:
            return await processor.process_meeting(transcript_value, custom_prompt=custom_prompt)
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.error("Meeting analysis failed: %s", exc, exc_info=True)
            fallback_type = meeting_type or processor.default_meeting_type
            return {
                "meeting_note": "",
                "task_items": [],
                "decision_items": [],
                "question_items": [],
                "token_usage": {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "context_tokens": 0,
                    "total_tokens": 0,
                    "price_usd": 0.0,
                },
                "is_informative": False,
                "meeting_type": fallback_type,
            }

    def _create_processor(self, meeting_type: Optional[str] = None) -> MeetingProcessor:
        model = self._instantiate_model()
        return MeetingProcessor(model=model, meeting_type=meeting_type)

    @staticmethod
    def _instantiate_model() -> Gemini:
        return _get_model()
