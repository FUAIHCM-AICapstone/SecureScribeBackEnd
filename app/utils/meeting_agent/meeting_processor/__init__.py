from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional

from agno.agent import Agent
from agno.models.message import Message
from pydantic import ValidationError

from app.utils.meeting_agent.agent_schema import (
    Decision,
    MeetingOutput,
    MeetingState,
    MeetingTypeResult,
    Question,
    Task,
)
from app.utils.meeting_agent.meeting_prompts import get_meeting_type_detector_prompt

LOGGER = logging.getLogger("MeetingProcessor")

if TYPE_CHECKING:
    from .informative_checker import InformativeChecker  # type: ignore  # noqa: F401
    from .output_generator import OutputGenerator  # type: ignore # noqa: F401
    from .simple_note_generator import SimpleMeetingNoteGenerator  # type: ignore # noqa: F401
    from .summary_extractor import SummaryExtractor  # type: ignore # noqa: F401

__all__ = ["MeetingProcessor", "TokenTracker", "update_tracker_from_metrics"]


class TokenTracker:
    """Track token usage reported by Agno."""

    def __init__(self) -> None:
        self.input_tokens = 0
        self.output_tokens = 0
        self.context_tokens = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.context_tokens

    def add_input_tokens(self, tokens: int) -> None:
        self.input_tokens += int(tokens)

    def add_output_tokens(self, tokens: int) -> None:
        self.output_tokens += int(tokens)

    def add_context_tokens(self, tokens: int) -> None:
        self.context_tokens += int(tokens)


def update_tracker_from_metrics(token_tracker: TokenTracker, metrics: Any) -> None:
    """Update tracker counters from an Agno metrics object."""
    if metrics is None:
        return
    input_tokens = getattr(metrics, "input_tokens", 0) or 0
    output_tokens = getattr(metrics, "output_tokens", 0) or 0
    total_tokens = getattr(metrics, "total_tokens", 0) or 0
    context_tokens = total_tokens - input_tokens - output_tokens
    if input_tokens:
        token_tracker.add_input_tokens(input_tokens)
    if output_tokens:
        token_tracker.add_output_tokens(output_tokens)
    if context_tokens > 0:
        token_tracker.add_context_tokens(context_tokens)


class MeetingTypeDetector(Agent):
    """Detect the meeting type based on transcript content."""

    VALID_TYPES = ("general", "project", "business", "product", "report")

    def __init__(self, model: Any, token_tracker: TokenTracker) -> None:
        instructions = [
            get_meeting_type_detector_prompt(),
            "Return JSON matching the MeetingTypeResult schema with fields meeting_type and optional reasoning.",
            "meeting_type must be one of: general, project, business, product, report.",
        ]
        super().__init__(
            name="MeetingTypeDetector",
            model=model,
            instructions=instructions,
            output_schema=MeetingTypeResult,
            structured_outputs=True,
            use_json_mode=True,
        )
        self._logger = logging.getLogger("MeetingTypeDetector")
        self._token_tracker = token_tracker

    async def detect(self, state: MeetingState) -> MeetingState:
        provided_type = (state.get("meeting_type") or "").strip().lower()
        if provided_type and provided_type != "general":
            self._logger.info("Using provided meeting type: %s", provided_type)
            state["meeting_type"] = provided_type
            self._append_message(state, f"meeting_type preset: {provided_type}")
            return state

        transcript = state.get("transcript") or ""
        if not transcript.strip():
            self._logger.warning("Transcript is empty, defaulting meeting type to general")
            return self._apply_result(
                state,
                MeetingTypeResult(meeting_type="general", reasoning="Transcript empty"),
            )

        sample = transcript[:2000]
        try:
            prompt = f"Review the meeting transcript excerpt and determine the meeting type.\n\nTranscript excerpt:\n{sample}\n\nValid meeting types: general, project, business, product, report.\nRespond in JSON following the MeetingTypeResult schema."
            user_message = Message(role="user", content=prompt)
            run_output = await self.arun([user_message], stream=False)
            update_tracker_from_metrics(self._token_tracker, run_output.metrics)
            content = run_output.content
            if isinstance(content, MeetingTypeResult):
                result = content
            else:
                result = MeetingTypeResult.model_validate(content)
        except ValidationError as exc:
            self._logger.error("Invalid response while detecting meeting type: %s", exc)
            return self._apply_result(
                state,
                MeetingTypeResult(
                    meeting_type="general",
                    reasoning="Could not parse detection result",
                ),
            )
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.error("Error during meeting type detection: %s", exc)
            return self._apply_result(
                state,
                MeetingTypeResult(meeting_type="general", reasoning="Detection failed"),
            )

        detected = (result.meeting_type or "general").strip().lower()
        if detected not in self.VALID_TYPES:
            self._logger.warning("Invalid meeting type received (%s), using general", detected)
            detected = "general"
        return self._apply_result(state, MeetingTypeResult(meeting_type=detected, reasoning=result.reasoning))

    def _apply_result(self, state: MeetingState, result: MeetingTypeResult) -> MeetingState:
        state["meeting_type"] = result.meeting_type
        message = result.reasoning or f"Detected meeting type: {result.meeting_type}"
        self._append_message(state, message)
        self._logger.info("Meeting type set to %s", result.meeting_type)
        return state

    @staticmethod
    def _append_message(state: MeetingState, content: str) -> None:
        messages = state.setdefault("messages", [])
        messages.append({"role": "agent", "agent": "MeetingTypeDetector", "content": content})


class MeetingProcessor:
    """Co-ordinate meeting processing across dedicated agents."""

    def __init__(self, model: Any, meeting_type: Optional[str] = "general") -> None:
        from .informative_checker import InformativeChecker
        from .output_generator import OutputGenerator
        from .simple_note_generator import SimpleMeetingNoteGenerator
        from .summary_extractor import SummaryExtractor

        self._logger = LOGGER
        self._token_tracker = TokenTracker()
        self._model = model
        self._default_meeting_type = (meeting_type or "general").lower()

        self._meeting_type_detector = MeetingTypeDetector(self._model, self._token_tracker)
        self._informative_checker = InformativeChecker(self._model, self._token_tracker)
        self._summary_extractor = SummaryExtractor(self._model, self._token_tracker)
        self._note_generator = SimpleMeetingNoteGenerator(self._model, self._token_tracker)
        self._output_generator = OutputGenerator(self._token_tracker)

    @property
    def default_meeting_type(self) -> str:
        return self._default_meeting_type

    async def process_meeting(self, transcript: str, custom_prompt: Optional[str] = None) -> Dict[str, Any]:
        transcript_value = transcript or ""
        state: MeetingState = {
            "messages": [],
            "transcript": transcript_value,
            "meeting_note": "",
            "task_items": [],
            "decision_items": [],
            "question_items": [],
            "token_usage": {},
            "is_informative": False,
            "meeting_type": self._default_meeting_type,
            "custom_prompt": custom_prompt,
        }
        try:
            state = await self._meeting_type_detector.detect(state)
            state = await self._informative_checker.check(state)

            if state.get("is_informative"):
                state = await self._summary_extractor.extract(state)
            else:
                state["task_items"] = []
                state["decision_items"] = []
                state["question_items"] = []

            state = await self._note_generator.generate(state)
            state = self._output_generator.generate(state)
            return self._format_success(state)
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.error("Error processing meeting: %s", exc, exc_info=True)
            return self._format_failure(state, str(exc))

    def _format_success(self, state: MeetingState) -> Dict[str, Any]:
        tasks = self._ensure_model_list(state.get("task_items", []), Task)
        decisions = self._ensure_model_list(state.get("decision_items", []), Decision)
        questions = self._ensure_model_list(state.get("question_items", []), Question)

        output = MeetingOutput(
            meeting_note=state.get("meeting_note", ""),
            task_items=tasks,
            decision_items=decisions,
            question_items=questions,
            token_usage=state.get("token_usage", self._current_token_usage()),
            is_informative=state.get("is_informative", False),
            meeting_type=state.get("meeting_type", "general"),
        )

        result = output.model_dump()
        result["task_items"] = [task.model_dump() for task in output.task_items]
        result["decision_items"] = [decision.model_dump() for decision in output.decision_items]
        result["question_items"] = [question.model_dump() for question in output.question_items]
        return result

    def _format_failure(self, state: MeetingState, message: str) -> Dict[str, Any]:
        self._logger.error("Returning fallback response: %s", message)
        return {
            "meeting_note": "",
            "task_items": [],
            "decision_items": [],
            "question_items": [],
            "token_usage": self._current_token_usage(),
            "is_informative": False,
            "meeting_type": state.get("meeting_type", "general"),
        }

    def _current_token_usage(self) -> Dict[str, Any]:
        return {
            "input_tokens": self._token_tracker.input_tokens,
            "output_tokens": self._token_tracker.output_tokens,
            "context_tokens": self._token_tracker.context_tokens,
            "total_tokens": self._token_tracker.total_tokens,
            "price_usd": 0.0,
        }

    @staticmethod
    def _ensure_model_list(items: Iterable[Any], model_cls: Any) -> list:
        converted = []
        for item in items:
            if isinstance(item, model_cls):
                converted.append(item)
            else:
                converted.append(model_cls(**item))
        return converted
