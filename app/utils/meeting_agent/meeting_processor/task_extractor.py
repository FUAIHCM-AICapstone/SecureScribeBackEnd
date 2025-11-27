from __future__ import annotations

import json
from textwrap import dedent
from typing import Any, List

from agno.agent import Agent
from agno.models.message import Message
from pydantic import ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.utils.meeting_agent.agent_schema import Task, TaskItems
from app.utils.meeting_agent.meeting_prompts import get_task_extraction_prompt


class TaskExtractor(Agent):
    """Extract structured tasks from meeting transcript with retry logic."""

    def __init__(self, model: Any) -> None:
        instructions = [
            "Analyse the transcript and extract tasks.",
            "Return JSON matching the TaskItems schema.",
        ]
        super().__init__(
            name="TaskExtractor",
            model=model,
            instructions=instructions,
            output_schema=TaskItems,
            structured_outputs=True,
            use_json_mode=True,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ValidationError, Exception)),
    )
    async def extract(self, transcript: str) -> List[Task]:
        """Extract tasks from transcript with automatic retry on failure."""
        if not transcript or not transcript.strip():
            return []

        context = {
            "transcript": transcript,
            "task_prompt": get_task_extraction_prompt(),
        }


        try:
            prompt = dedent(
                f"""
                Extract tasks from the meeting transcript.

                Context (JSON):
                {json.dumps(context, ensure_ascii=False, indent=2)}

                Respond in JSON following the TaskItems schema.
                """
            ).strip()

            user_message = Message(role="user", content=prompt)
            run_output = await self.arun([user_message], stream=False)
            content = run_output.content

            if isinstance(content, TaskItems):
                result = content
            else:
                result = TaskItems.model_validate(content)

            if result.tasks:
                for i, task in enumerate(result.tasks):
                    print(f"Extracted Task {i + 1}: {task.title} - {task.description}")
            return result.tasks

        except ValidationError as exc:
            print(f"[TaskExtractor] Validation error: {exc}")
            raise  # Re-raise for retry

        except Exception as exc:
            print(f"[TaskExtractor] Unexpected error: {exc}")
            raise  # Re-raise for retry
