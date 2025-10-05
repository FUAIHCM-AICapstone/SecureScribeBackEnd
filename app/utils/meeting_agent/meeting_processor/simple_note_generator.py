from __future__ import annotations

import json
import logging
from textwrap import dedent
from typing import Any, Dict

from agno.agent import Agent
from agno.models.message import Message
from pydantic import ValidationError

from app.utils.meeting_agent.agent_schema import MeetingNoteResult, MeetingState
from app.utils.meeting_agent.meeting_prompts import get_prompt_for_meeting_type
from . import TokenTracker, update_tracker_from_metrics

LOGGER = logging.getLogger("SimpleMeetingNoteGenerator")


class SimpleMeetingNoteGenerator(Agent):
    """Generate a concise Vietnamese meeting note in Markdown."""

    def __init__(self, model: Any, token_tracker: TokenTracker) -> None:
        instructions = [
            "Create a Markdown meeting note in Vietnamese based on the provided context.",
            "Return JSON matching the MeetingNoteResult schema.",
        ]
        super().__init__(
            name="SimpleMeetingNoteGenerator",
            model=model,
            instructions=instructions,
            output_schema=MeetingNoteResult,
            structured_outputs=True,
            use_json_mode=True,
        )
        self._logger = LOGGER
        self._token_tracker = token_tracker

    async def generate(self, state: MeetingState) -> MeetingState:
        if not state.get("is_informative"):
            note = "Không đủ thông tin để tạo ghi chú chi tiết."
            self._logger.warning("Transcript marked as not informative, returning default note")
            state["meeting_note"] = note
            messages = state.setdefault("messages", [])
            messages.append(
                {
                    "role": "agent",
                    "agent": "SimpleMeetingNoteGenerator",
                    "content": "Transcript not informative -> default note created",
                }
            )
            return state

        transcript = (state.get("transcript") or "").strip()
        if len(transcript) < 50:
            note = "Không đủ thông tin để tạo ghi chú cuộc họp."
            state["meeting_note"] = note
            messages = state.setdefault("messages", [])
            messages.append(
                {
                    "role": "agent",
                    "agent": "SimpleMeetingNoteGenerator",
                    "content": "Transcript too short for detailed note",
                }
            )
            return state

        meeting_type = state.get("meeting_type", "general")
        custom_prompt = state.get("custom_prompt")
        context: Dict[str, Any] = {
            "meeting_type": meeting_type,
            "meeting_note_prompt": get_prompt_for_meeting_type(meeting_type),
            "transcript": transcript,
            "custom_prompt": custom_prompt,
            "tasks": state.get("task_items", []),
            "decisions": state.get("decision_items", []),
            "questions": state.get("question_items", []),
        }

        try:
            prompt = dedent(
                f"""
                Create a concise Vietnamese meeting note in Markdown format using the provided context.

                Context (JSON):
                {json.dumps(context, ensure_ascii=False, indent=2)}

                Remove triple backticks if present. Respond in JSON following the MeetingNoteResult schema.
                """
            ).strip()
            user_message = Message(role="user", content=prompt)
            run_output = await self.arun([user_message], stream=False)
            update_tracker_from_metrics(self._token_tracker, run_output.metrics)
            content = run_output.content
            if isinstance(content, MeetingNoteResult):
                result = content
            else:
                result = MeetingNoteResult.model_validate(content)
            note = (result.meeting_note or "").replace("```", "").strip()
        except ValidationError as exc:
            self._logger.error("Failed to parse meeting note response: %s", exc)
            note = "Không thể tạo ghi chú cuộc họp do lỗi định dạng."  # fallback message
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.error("Error generating meeting note: %s", exc)
            note = "Không thể tạo ghi chú cuộc họp do lỗi không xác định."

        state["meeting_note"] = note
        messages = state.setdefault("messages", [])
        messages.append(
            {"role": "agent", "agent": "SimpleMeetingNoteGenerator", "content": "Generated meeting note"}
        )
        return state
