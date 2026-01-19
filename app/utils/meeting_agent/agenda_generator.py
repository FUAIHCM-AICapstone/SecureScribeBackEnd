from __future__ import annotations

from typing import Any, List, Optional

from agno.agent import Agent
from pydantic import BaseModel, Field, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.utils.meeting_agent.meeting_prompts import get_prompt_for_meeting_agenda


class AgendaResult(BaseModel):
    """Schema for meeting agenda generation result."""

    agenda: str = Field(description="Generated meeting agenda in Markdown format")
    meeting_type: Optional[str] = Field(default=None, description="Detected meeting type")
    key_topics: List[str] = Field(default_factory=list, description="Key topics identified")
    suggested_duration_minutes: int = Field(default=60, description="Suggested meeting duration")


class AgendaGenerator(Agent):
    """Generate a structured Vietnamese meeting agenda in Markdown based on context."""

    def __init__(self, model: Any) -> None:
        instructions = [
            "Create a structured Markdown meeting agenda in Vietnamese based on the provided documents and context.",
            "Return JSON matching the AgendaResult schema.",
            "Focus on practical agenda items with time allocations.",
            "Organize items logically from opening to closing.",
        ]
        super().__init__(
            name="AgendaGenerator",
            model=model,
            instructions=instructions,
            output_schema=AgendaResult,
            structured_outputs=True,
            use_json_mode=True,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ValidationError, Exception)),
        before_sleep=lambda retry_state: print(f"[AgendaGenerator] Retrying agenda generation... attempt {retry_state.attempt_number}"),
    )
    async def generate(
        self,
        documents: List[str],
        meeting_type_hint: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        transcript: Optional[str] = None,
    ) -> str:
        """
        Generate meeting agenda from documents and optional transcript.

        Args:
            documents: List of document texts from indexed files
            meeting_type_hint: Type hint for meeting (business, technical, brainstorming, etc.)
            custom_prompt: Custom instructions for agenda generation
            transcript: Optional transcript from meeting

        Returns:
            Generated agenda in Markdown format
        """
        # Validate inputs
        if not documents:
            documents = []

        # Combine documents into context
        combined_context = "\n\n---\n\n".join([doc for doc in documents if doc and doc.strip()])

        if not combined_context or not combined_context.strip():
            if transcript and transcript.strip():
                combined_context = transcript
            else:
                return "Không đủ thông tin để tạo chương trình họp. Vui lòng cung cấp tài liệu hoặc nội dung cuộc họp."

        if len(combined_context) < 50:
            return "Không đủ thông tin để tạo chương trình họp. Tài liệu quá ngắn."

        # Get prompt template for agenda
        prompt = get_prompt_for_meeting_agenda(
            meeting_type=meeting_type_hint,
            custom_instructions=custom_prompt,
        )

        # Create full prompt with context
        full_prompt = f"{prompt}\n\n--- CONTEXT FROM DOCUMENTS ---\n\n{combined_context}"

        try:
            # Call LLM to generate agenda
            run_output = await self.arun(full_prompt)

            # Extract agenda from RunOutput
            if run_output and hasattr(run_output, 'messages') and len(run_output.messages) > 0:
                # Get the last message which contains the response
                last_message = run_output.messages[-1]
                if hasattr(last_message, 'content'):
                    content = last_message.content
                    # If content is a dict (parsed as AgendaResult), extract agenda
                    if isinstance(content, dict) and 'agenda' in content:
                        return content['agenda']
                    # If content is a string, assume it's the agenda
                    elif isinstance(content, str):
                        return content
            
            return "Không thể tạo chương trình họp từ tài liệu được cung cấp."

        except ValidationError as ve:
            print(f"[AgendaGenerator] Validation error: {ve}")
            raise
        except Exception as e:
            print(f"[AgendaGenerator] Error generating agenda: {e}")
            raise


async def generate_agenda_from_documents(
    documents: List[str],
    model: Any,
    meeting_type_hint: Optional[str] = None,
    custom_prompt: Optional[str] = None,
    transcript: Optional[str] = None,
) -> tuple[str, dict]:
    """
    Generate meeting agenda from documents.

    Args:
        documents: List of document texts
        model: LLM model instance
        meeting_type_hint: Type hint for meeting
        custom_prompt: Custom instructions
        transcript: Optional transcript

    Returns:
        Tuple of (agenda_content, token_usage)
    """
    generator = AgendaGenerator(model)

    agenda = await generator.generate(
        documents=documents,
        meeting_type_hint=meeting_type_hint,
        custom_prompt=custom_prompt,
        transcript=transcript,
    )

    # Token usage from model (if available)
    token_usage = {}
    if hasattr(generator, "model") and hasattr(generator.model, "token_usage"):
        token_usage = generator.model.token_usage

    return agenda, token_usage
