from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional

from agno.agent import Agent
from agno.models.message import Message
from pydantic import ValidationError

from app.utils.meeting_agent.agent_schema import (
    MeetingOutput,
    MeetingState,
    MeetingTypeResult,
    Task,
)
from app.utils.meeting_agent.meeting_prompts import get_meeting_type_detector_prompt

if TYPE_CHECKING:
    from .informative_checker import InformativeChecker  # type: ignore  # noqa: F401
    from .simple_note_generator import SimpleMeetingNoteGenerator  # type: ignore # noqa: F401
    from .summary_extractor import SummaryExtractor  # type: ignore # noqa: F401

__all__ = ["MeetingProcessor"]


class MeetingTypeDetector(Agent):
    """Detect the meeting type based on transcript content."""

    VALID_TYPES = ("general", "project", "business", "product", "report")

    def __init__(self, model: Any) -> None:
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
        self._model = model

    async def detect(self, state: MeetingState) -> MeetingState:
        provided_type = (state.get("meeting_type") or "").strip().lower()
        if provided_type and provided_type != "general":
            print(f"[MeetingTypeDetector] Using provided meeting type: {provided_type}")
            state["meeting_type"] = provided_type
            self._append_message(state, f"meeting_type preset: {provided_type}")
            return state

        transcript = state.get("transcript") or ""
        if not transcript.strip():
            print("[MeetingTypeDetector] Transcript is empty, defaulting meeting type to general")
            return self._apply_result(
                state,
                MeetingTypeResult(meeting_type="general", reasoning="Transcript empty"),
            )

        sample = transcript[:2000]
        try:
            prompt = f"Review the meeting transcript excerpt and determine the meeting type.\n\nTranscript excerpt:\n{sample}\n\nValid meeting types: general, project, business, product, report.\nRespond in JSON following the MeetingTypeResult schema."
            user_message = Message(role="user", content=prompt)
            run_output = await self.arun([user_message], stream=False)
            content = run_output.content
            if isinstance(content, MeetingTypeResult):
                result = content
            else:
                result = MeetingTypeResult.model_validate(content)
        except ValidationError as exc:
            print(f"[MeetingTypeDetector] Invalid response while detecting meeting type: {exc}")
            return self._apply_result(
                state,
                MeetingTypeResult(
                    meeting_type="general",
                    reasoning="Could not parse detection result",
                ),
            )
        except Exception as exc:
            print(f"[MeetingTypeDetector] Error during meeting type detection: {exc}")
            return self._apply_result(
                state,
                MeetingTypeResult(meeting_type="general", reasoning="Detection failed"),
            )

        detected = (result.meeting_type or "general").strip().lower()
        if detected not in self.VALID_TYPES:
            print(f"[MeetingTypeDetector] Invalid meeting type received ({detected}), using general")
            detected = "general"
        return self._apply_result(state, MeetingTypeResult(meeting_type=detected, reasoning=result.reasoning))

    def _apply_result(self, state: MeetingState, result: MeetingTypeResult) -> MeetingState:
        state["meeting_type"] = result.meeting_type
        message = result.reasoning or f"Detected meeting type: {result.meeting_type}"
        self._append_message(state, message)
        print(f"[MeetingTypeDetector] Meeting type set to {result.meeting_type}")
        return state

    @staticmethod
    def _append_message(state: MeetingState, content: str) -> None:
        messages = state.setdefault("messages", [])
        messages.append({"role": "agent", "agent": "MeetingTypeDetector", "content": content})


class MeetingProcessor:
    """Co-ordinate meeting processing across dedicated agents."""

    def __init__(self, model: Any, meeting_type: Optional[str] = "general") -> None:
        from .informative_checker import InformativeChecker
        from .simple_note_generator import SimpleMeetingNoteGenerator
        from .summary_extractor import SummaryExtractor

        self._model = model
        self._default_meeting_type = (meeting_type or "general").lower()

        self._meeting_type_detector = MeetingTypeDetector(self._model)
        self._informative_checker = InformativeChecker(self._model)
        self._summary_extractor = SummaryExtractor(self._model)
        self._note_generator = SimpleMeetingNoteGenerator(self._model)

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

            state = await self._note_generator.generate(state)
            return self._format_success(state)
        except Exception as exc:
            print(f"[MeetingProcessor] Error processing meeting: {exc}")
            return self._format_failure(state, str(exc))

    def _format_success(self, state: MeetingState) -> Dict[str, Any]:
        tasks = self._ensure_model_list(state.get("task_items", []), Task)

        output = MeetingOutput(
            meeting_note=state.get("meeting_note", ""),
            task_items=tasks,
            is_informative=state.get("is_informative", False),
            meeting_type=state.get("meeting_type", "general"),
        )

        result = output.model_dump()
        result["task_items"] = [task.model_dump() for task in output.task_items]
        return result

    def _format_failure(self, state: MeetingState, message: str) -> Dict[str, Any]:
        print(f"[MeetingProcessor] Returning fallback response: {message}")
        return {
            "meeting_note": "",
            "task_items": [],
            "is_informative": False,
            "meeting_type": state.get("meeting_type", "general"),
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
