from __future__ import annotations

import json
from textwrap import dedent
from typing import Any, Dict

from agno.agent import Agent
from agno.models.message import Message
from pydantic import ValidationError

from app.utils.meeting_agent.agent_schema import MeetingNoteResult, MeetingState
from app.utils.meeting_agent.meeting_prompts import get_prompt_for_meeting_type


class SimpleMeetingNoteGenerator(Agent):
    """Generate a concise Vietnamese meeting note in Markdown."""

    def __init__(self, model: Any) -> None:
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

    async def generate(self, state: MeetingState) -> MeetingState:
        if not state.get("is_informative"):
            note = "Không đủ thông tin để tạo ghi chú chi tiết."
            print("[SimpleMeetingNoteGenerator] Transcript marked as not informative, returning default note")
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

        if custom_prompt:
            print(f"[SimpleMeetingNoteGenerator] Using custom_prompt: {custom_prompt[:100]}...")

        context: Dict[str, Any] = {
            "meeting_type": meeting_type,
            "meeting_note_prompt": get_prompt_for_meeting_type(meeting_type),
            "transcript": transcript,
            "custom_prompt": custom_prompt,
            "tasks": state.get("task_items", []),
        }

        try:
            prompt_instruction = ""
            if custom_prompt:
                prompt_instruction = f"""
CUSTOM INSTRUCTION (Apply this first if provided):
{custom_prompt}

After applying the custom instruction above, also follow the context below:
"""
            else:
                prompt_instruction = "Create a concise Vietnamese meeting note in Markdown format using the provided context.\n"

            prompt = dedent(
                f"""
                {prompt_instruction}

                Context (JSON):
                {json.dumps(context, ensure_ascii=False, indent=2)}

                Remove triple backticks if present. Respond in JSON following the MeetingNoteResult schema.
                """
            ).strip()
            user_message = Message(role="user", content=prompt)
            run_output = await self.arun([user_message], stream=False)
            content = run_output.content
            if isinstance(content, MeetingNoteResult):
                result = content
            else:
                result = MeetingNoteResult.model_validate(content)
            note = (result.meeting_note or "").replace("```", "").strip()
        except ValidationError as exc:
            print(f"[SimpleMeetingNoteGenerator] Failed to parse meeting note response: {exc}")
            note = "Không thể tạo ghi chú cuộc họp do lỗi định dạng."
        except Exception as exc:
            print(f"[SimpleMeetingNoteGenerator] Error generating meeting note: {exc}")
            note = "Không thể tạo ghi chú cuộc họp do lỗi không xác định."

        state["meeting_note"] = note
        messages = state.setdefault("messages", [])
        messages.append({"role": "agent", "agent": "SimpleMeetingNoteGenerator", "content": "Generated meeting note"})
        return state
