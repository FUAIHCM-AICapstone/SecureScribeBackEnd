from __future__ import annotations

import json
from textwrap import dedent
from typing import Any, Dict, List, Optional

from agno.agent import Agent
from agno.models.message import Message
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.utils.meeting_agent.agent_schema import MeetingNoteResult, Task
from app.utils.meeting_agent.meeting_prompts import get_prompt_for_meeting_type


class NoteGenerator(Agent):
    """Generate a concise Vietnamese meeting note in Markdown with retry logic."""

    def __init__(self, model: Any) -> None:
        instructions = [
            "Create a Markdown meeting note in Vietnamese based on the provided context.",
            "Return JSON matching the MeetingNoteResult schema.",
        ]
        super().__init__(
            name="NoteGenerator",
            model=model,
            instructions=instructions,
            output_schema=MeetingNoteResult,
            structured_outputs=True,
            use_json_mode=True,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ValidationError, Exception)),
        before_sleep=lambda retry_state: print(f"[NoteGenerator] Retrying note generation... attempt {retry_state.attempt_number}"),
    )
    async def generate(
        self,
        transcript: str,
        tasks: List[Task],
        custom_prompt: Optional[str] = None,
    ) -> str:
        """Generate meeting note from transcript with automatic retry on failure."""
        if not transcript or not transcript.strip():
            print("[NoteGenerator] Transcript empty, returning default note")
            return "Không đủ thông tin để tạo ghi chú cuộc họp."

        if len(transcript) < 50:
            print("[NoteGenerator] Transcript too short, returning default note")
            return "Không đủ thông tin để tạo ghi chú cuộc họp."

        if custom_prompt:
            print(f"[NoteGenerator] Using custom_prompt: {custom_prompt[:100]}...")

        # Convert tasks to dict for JSON serialization
        tasks_dict = [task.model_dump() if hasattr(task, "model_dump") else task for task in tasks]

        context: Dict[str, Any] = {
            "meeting_type": "general",
            "meeting_note_prompt": get_prompt_for_meeting_type("general"),
            "transcript": transcript,
            "custom_prompt": custom_prompt,
            "tasks": tasks_dict,
        }

        print(f"[NoteGenerator] Starting note generation - transcript_length: {len(transcript)}, tasks_count: {len(tasks)}")

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

            if not note:
                print("[NoteGenerator] Generated note is empty, using fallback")
                note = "Không thể tạo ghi chú cuộc họp."
            else:
                print(f"[NoteGenerator] Successfully generated note, length: {len(note)} characters")

            return note

        except ValidationError as exc:
            print(f"[NoteGenerator] Validation error: {exc}")
            raise  # Re-raise for retry

        except Exception as exc:
            print(f"[NoteGenerator] Unexpected error during generation: {exc}")
            print(f"[NoteGenerator] Exception type: {type(exc).__name__}")
            raise  # Re-raise for retry
