from __future__ import annotations

import json
import logging
from textwrap import dedent
from typing import Any

from agno.agent import Agent
from agno.models.message import Message
from pydantic import ValidationError

from app.utils.meeting_agent.agent_schema import MeetingState, SummaryExtractionResult
from app.utils.meeting_agent.meeting_prompts import (
    get_decision_extraction_prompt,
    get_question_extraction_prompt,
    get_task_extraction_prompt,
)

from . import TokenTracker, update_tracker_from_metrics

LOGGER = logging.getLogger("SummaryExtractor")


class SummaryExtractor(Agent):
    """Extract structured tasks, decisions, and questions."""

    def __init__(self, model: Any, token_tracker: TokenTracker) -> None:
        instructions = [
            "Analyse the transcript and extract tasks, decisions, and questions.",
            "Return JSON matching the SummaryExtractionResult schema.",
        ]
        super().__init__(
            name="SummaryExtractor",
            model=model,
            instructions=instructions,
            output_schema=SummaryExtractionResult,
            structured_outputs=True,
            use_json_mode=True,
        )
        self._logger = LOGGER
        self._token_tracker = token_tracker

    async def extract(self, state: MeetingState) -> MeetingState:
        transcript = (state.get("transcript") or "").strip()
        if not transcript:
            self._logger.warning("Transcript empty, skipping structured extraction")
            state["task_items"] = []
            state["decision_items"] = []
            state["question_items"] = []
            return state

        meeting_type = state.get("meeting_type", "general")
        context = {
            "transcript": transcript,
            "meeting_type": meeting_type,
            "task_prompt": get_task_extraction_prompt(meeting_type),
            "decision_prompt": get_decision_extraction_prompt(meeting_type),
            "question_prompt": get_question_extraction_prompt(meeting_type),
        }

        try:
            prompt = dedent(
                f"""
                Extract tasks, decisions, and questions from the meeting transcript.

                Context (JSON):
                {json.dumps(context, ensure_ascii=False, indent=2)}

                Respond in JSON following the SummaryExtractionResult schema.
                """
            ).strip()
            user_message = Message(role="user", content=prompt)
            run_output = await self.arun([user_message], stream=False)
            update_tracker_from_metrics(self._token_tracker, run_output.metrics)
            content = run_output.content
            if isinstance(content, SummaryExtractionResult):
                result = content
            else:
                result = SummaryExtractionResult.model_validate(content)
        except ValidationError as exc:
            self._logger.error("Failed to parse summary extraction result: %s", exc)
            result = SummaryExtractionResult()
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.error("Error during summary extraction: %s", exc)
            result = SummaryExtractionResult()

        state["task_items"] = [task.model_dump() for task in result.tasks]
        state["decision_items"] = [decision.model_dump() for decision in result.decisions]
        state["question_items"] = [question.model_dump() for question in result.questions]

        messages = state.setdefault("messages", [])
        messages.append(
            {
                "role": "agent",
                "agent": "SummaryExtractor",
                "content": (f"tasks={len(result.tasks)}, decisions={len(result.decisions)}, questions={len(result.questions)}"),
            }
        )
        return state
