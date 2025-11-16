from __future__ import annotations

import json
from textwrap import dedent
from typing import Any

from agno.agent import Agent
from agno.models.message import Message
from pydantic import ValidationError

from app.utils.meeting_agent.agent_schema import MeetingState, TaskItems
from app.utils.meeting_agent.meeting_prompts import get_task_extraction_prompt


class SummaryExtractor(Agent):
    """Extract structured tasks only."""

    def __init__(self, model: Any) -> None:
        instructions = [
            "Analyse the transcript and extract tasks.",
            "Return JSON matching the TaskItems schema.",
        ]
        super().__init__(
            name="SummaryExtractor",
            model=model,
            instructions=instructions,
            output_schema=TaskItems,
            structured_outputs=True,
            use_json_mode=True,
        )

    async def extract(self, state: MeetingState) -> MeetingState:
        transcript = (state.get("transcript") or "").strip()
        if not transcript:
            print("[SummaryExtractor] Transcript empty, skipping structured extraction")
            state["task_items"] = []
            return state

        meeting_type = state.get("meeting_type", "general")
        context = {
            "transcript": transcript,
            "meeting_type": meeting_type,
            "task_prompt": get_task_extraction_prompt(),
        }

        print(f"[SummaryExtractor] Starting task extraction - meeting_type: {meeting_type}, transcript_length: {len(transcript)}")

        try:
            prompt = dedent(
                f"""
                Extract tasks from the meeting transcript.

                Context (JSON):
                {json.dumps(context, ensure_ascii=False, indent=2)}

                Respond in JSON following the TaskItems schema.
                """
            ).strip()
            print(f"[SummaryExtractor] Sending extraction prompt, context length: {len(json.dumps(context, ensure_ascii=False))}")
            user_message = Message(role="user", content=prompt)
            run_output = await self.arun([user_message], stream=False)
            content = run_output.content
            print(f"[SummaryExtractor] LLM response received, content type: {type(content).__name__}")
            
            if isinstance(content, TaskItems):
                result = content
                print(f"[SummaryExtractor] Response already TaskItems, tasks count: {len(result.tasks)}")
            else:
                print(f"[SummaryExtractor] Attempting to validate response: {str(content)[:200]}...")
                result = TaskItems.model_validate(content)
                print(f"[SummaryExtractor] Validation successful, extracted {len(result.tasks)} tasks")
        except ValidationError as exc:
            print(f"[SummaryExtractor] Failed to parse summary extraction result: {exc}")
            print(f"[SummaryExtractor] Error details - field errors: {exc.errors()}")
            result = TaskItems()
        except Exception as exc:
            print(f"[SummaryExtractor] Error during summary extraction: {exc}")
            print(f"[SummaryExtractor] Exception type: {type(exc).__name__}")
            result = TaskItems()

        state["task_items"] = [task.model_dump() for task in result.tasks]
        print(f"[SummaryExtractor] Task extraction complete - stored {len(state['task_items'])} tasks in state")
        
        if result.tasks:
            print("[SummaryExtractor] Extracted tasks:")
            for i, task in enumerate(result.tasks):
                print(f"  [{i+1}] {task.description[:80]}...")

        messages = state.setdefault("messages", [])
        messages.append(
            {
                "role": "agent",
                "agent": "SummaryExtractor",
                "content": (f"tasks={len(result.tasks)}"),
            }
        )
        return state
