from __future__ import annotations

import logging
from typing import Any, Dict

from agno.agent import Agent

from app.utils.meeting_agent.agent_schema import MeetingOutput, MeetingState
from . import TokenTracker

LOGGER = logging.getLogger("OutputGenerator")


class OutputGenerator(Agent):
    """Assemble the final meeting output payload."""

    def __init__(self, token_tracker: TokenTracker) -> None:
        super().__init__(name="OutputGenerator", model=None, output_schema=MeetingOutput)
        self._logger = LOGGER
        self._token_tracker = token_tracker

    def generate(self, state: MeetingState) -> MeetingState:
        token_usage: Dict[str, Any] = {
            "input_tokens": self._token_tracker.input_tokens,
            "output_tokens": self._token_tracker.output_tokens,
            "context_tokens": self._token_tracker.context_tokens,
            "total_tokens": self._token_tracker.total_tokens,
            "price_usd": 0.0,
        }
        state["token_usage"] = token_usage
        messages = state.setdefault("messages", [])
        messages.append({"role": "agent", "agent": "OutputGenerator", "content": "Assembled final output"})
        return state
