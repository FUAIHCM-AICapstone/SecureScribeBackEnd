from __future__ import annotations

from textwrap import dedent
from typing import Any

from agno.agent import Agent
from agno.models.message import Message
from pydantic import ValidationError

from app.utils.meeting_agent.agent_schema import InformativeCheckResult, MeetingState


class InformativeChecker(Agent):
    """Agent that determines whether a transcript contains enough signal."""

    def __init__(self, model: Any) -> None:
        instructions = [
            "Evaluate whether the meeting transcript contains sufficient meaningful content.",
            "Return JSON matching the InformativeCheckResult schema.",
        ]
        super().__init__(
            name="InformativeChecker",
            model=model,
            instructions=instructions,
            output_schema=InformativeCheckResult,
            structured_outputs=True,
            use_json_mode=True,
        )

    async def check(self, state: MeetingState) -> MeetingState:
        transcript = (state.get("transcript") or "").strip()
        if not transcript:
            print("[InformativeChecker] Transcript empty, marking as not informative")
            return self._apply_result(state, InformativeCheckResult(is_informative=False, reason="Transcript empty"))

        if len(transcript) < 100:
            reason = f"Transcript length {len(transcript)} < 100 characters"
            print(f"[InformativeChecker] {reason}")
            return self._apply_result(state, InformativeCheckResult(is_informative=False, reason=reason))

        try:
            prompt = dedent(
                f"""
                Evaluate whether the meeting transcript contains enough meaningful content.

                Meeting type: {state.get("meeting_type", "general")}
                Minimum informative length: 100 characters.

                Transcript:
                {transcript}

                Respond in JSON following the InformativeCheckResult schema.
                """
            ).strip()
            user_message = Message(role="user", content=prompt)
            run_output = await self.arun([user_message], stream=False)
            content = run_output.content
            if isinstance(content, InformativeCheckResult):
                result = content
            else:
                result = InformativeCheckResult.model_validate(content)
        except ValidationError as exc:
            print(f"[InformativeChecker] Failed to parse informative checker response: {exc}")
            result = InformativeCheckResult(is_informative=True, reason="Validation error fallback")
        except Exception as exc:
            print(f"[InformativeChecker] Error during informative check: {exc}")
            result = InformativeCheckResult(is_informative=True, reason="Checker error fallback")

        return self._apply_result(state, result)

    def _apply_result(self, state: MeetingState, result: InformativeCheckResult) -> MeetingState:
        state["is_informative"] = result.is_informative
        message = result.reason or ("Transcript is informative" if result.is_informative else "Transcript is not informative")
        messages = state.setdefault("messages", [])
        messages.append({"role": "agent", "agent": "InformativeChecker", "content": message})
        return state
