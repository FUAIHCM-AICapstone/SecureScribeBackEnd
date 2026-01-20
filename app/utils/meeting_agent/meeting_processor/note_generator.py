from __future__ import annotations

import json
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple

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
        agenda: Optional[str] = None,
        project_files_context: Optional[str] = None,
        meeting_files_context: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate meeting note from transcript with automatic retry on failure."""
        if not transcript or not transcript.strip():
            return "Không đủ thông tin để tạo ghi chú cuộc họp.", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        if len(transcript) < 50:
            return "Không đủ thông tin để tạo ghi chú cuộc họp.", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        # Convert tasks to dict for JSON serialization
        tasks_dict = [task.model_dump() if hasattr(task, "model_dump") else task for task in tasks]

        context: Dict[str, Any] = {
            "meeting_type": "general",
            "meeting_note_prompt": get_prompt_for_meeting_type("general"),
            "transcript": transcript,
            "custom_prompt": custom_prompt,
            "tasks": tasks_dict,
        }

        # Add optional context
        if agenda:
            context["agenda"] = agenda
        if project_files_context:
            context["project_files_context"] = project_files_context
        if meeting_files_context:
            context["meeting_files_context"] = meeting_files_context

        try:
            prompt_instruction = ""
            if custom_prompt:
                prompt_instruction = f"""
CUSTOM INSTRUCTION (Apply this first if provided):
{custom_prompt}

After applying the custom instruction above, also follow the priority guidelines below:
"""
            else:
                prompt_instruction = "Create a concise Vietnamese meeting note in Markdown format using the provided context.\n"

            # Add priority guidelines to ensure focus on transcript
            priority_guidelines = """
PRIORITY GUIDELINES (CRITICAL - Must follow):
1. PRIMARY FOCUS (HIGH PRIORITY): "transcript" field
   - This is the MAIN content of the meeting
   - Extract key points, decisions, and actions from here
   - Your output MUST be primarily based on transcript content

2. SECONDARY CONTEXT (MEDIUM PRIORITY): "meeting_files_context" field
   - Use to supplement and clarify points from transcript
   - DO NOT let this override or dominate the note
   - Only include if directly relevant to meeting discussion

3. REFERENCE CONTEXT (LOW PRIORITY): "agenda", "project_files_context" fields
   - Use ONLY to understand business/project context
   - DO NOT include extensive project details unless mentioned in transcript
   - If meeting is short (5 min) but project files are long (100 pages), 
     focus on what was actually discussed in the meeting, not project documents
   - Project context should occupy <20% of the output

RULE: If project/agenda context conflicts with transcript content, 
       ALWAYS prioritize what was actually said in the meeting.

OUTPUT REQUIREMENT:
- Summarize meeting transcript content accurately
- Add meeting files details only when transcript references them
- Mention project context ONLY if meeting specifically discussed it
- If input has 5-min transcript + 100-page project doc:
  Output should be 80% transcript summary + 20% project context
"""

            prompt = dedent(
                f"""
                {priority_guidelines}

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

            # Extract token usage from run_output.metrics
            token_usage = {}
            if hasattr(run_output, "metrics") and run_output.metrics:
                token_usage = {
                    "input_tokens": getattr(run_output.metrics, "input_tokens", None),
                    "output_tokens": getattr(run_output.metrics, "output_tokens", None),
                    "total_tokens": getattr(run_output.metrics, "total_tokens", None),
                }

            if not note:
                note = "Không thể tạo ghi chú cuộc họp."
            else:
                print("[NoteGenerator] Generated meeting note successfully.")

            return note, token_usage

        except ValidationError as exc:
            print(f"[NoteGenerator] Validation error during generation: {exc}")
            raise  # Re-raise for retry

        except Exception as exc:
            print(f"[NoteGenerator] Unexpected error during generation: {exc}")
            raise  # Re-raise for retry

    async def generate_with_empty_fallback(
        self,
        transcript: str,
        tasks: List[Task],
        custom_prompt: Optional[str] = None,
        agenda: Optional[str] = None,
        project_files_context: Optional[str] = None,
        meeting_files_context: Optional[str] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """Wrapper to return fallback on failure instead of raising."""
        try:
            return await self.generate(
                transcript,
                tasks,
                custom_prompt,
                agenda=agenda,
                project_files_context=project_files_context,
                meeting_files_context=meeting_files_context,
            )
        except Exception:
            return "Không thể tạo ghi chú cuộc họp do lỗi xử lý.", {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
