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
        before_sleep=lambda retry_state: print(f"[TaskExtractor] Retrying task extraction... attempt {retry_state.attempt_number}"),
    )
    async def extract(self, transcript: str) -> List[Task]:
        """Extract tasks from transcript with automatic retry on failure."""
        if not transcript or not transcript.strip():
            print("[TaskExtractor] Transcript empty, returning empty task list")
            return []

        context = {
            "transcript": transcript,
            "task_prompt": get_task_extraction_prompt(),
        }

        print(f"[TaskExtractor] Starting task extraction - transcript_length: {len(transcript)}")

        try:
            prompt = dedent(
                f"""
                Extract tasks from the meeting transcript.

                Context (JSON):
                {json.dumps(context, ensure_ascii=False, indent=2)}

                Respond in JSON following the TaskItems schema.
                """
            ).strip()

            print(f"[TaskExtractor] Sending extraction prompt, context length: {len(json.dumps(context, ensure_ascii=False))}")
            user_message = Message(role="user", content=prompt)
            run_output = await self.arun([user_message], stream=False)
            content = run_output.content
            print(f"[TaskExtractor] LLM response received, content type: {type(content).__name__}")

            if isinstance(content, TaskItems):
                result = content
                print(f"[TaskExtractor] Response already TaskItems, tasks count: {len(result.tasks)}")
            else:
                print(f"[TaskExtractor] Attempting to validate response: {str(content)[:200]}...")
                result = TaskItems.model_validate(content)
                print(f"[TaskExtractor] Validation successful, extracted {len(result.tasks)} tasks")

            if result.tasks:
                print(f"[TaskExtractor] Successfully extracted {len(result.tasks)} tasks:")
                for i, task in enumerate(result.tasks):
                    print(f"  [{i + 1}] {task.description[:80]}...")

            return result.tasks

        except ValidationError as exc:
            print(f"[TaskExtractor] Validation error: {exc}")
            print(f"[TaskExtractor] Error details - field errors: {exc.errors()}")
            raise  # Re-raise for retry

        except Exception as exc:
            print(f"[TaskExtractor] Unexpected error during extraction: {exc}")
            print(f"[TaskExtractor] Exception type: {type(exc).__name__}")
            raise  # Re-raise for retry
