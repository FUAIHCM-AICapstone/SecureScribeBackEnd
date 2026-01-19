from __future__ import annotations

from typing import Any, List, Optional

from agno.agent import Agent
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.utils.meeting_agent.meeting_prompts import get_prompt_for_meeting_agenda


class AgendaGenerator(Agent):
    """Generate a Vietnamese meeting agenda in Markdown format based on context."""

    def __init__(self, model: Any) -> None:
        instructions = [
            "Create a detailed Markdown meeting agenda in Vietnamese based on the provided documents and context.",
            "Format as clean Markdown with sections, subsections, time allocations, and action items.",
            "Focus on practical agenda items with clear time allocations.",
            "Organize items logically from opening to closing.",
        ]
        super().__init__(
            name="AgendaGenerator",
            model=model,
            instructions=instructions,
            markdown=True,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda retry_state: print(f"[AgendaGenerator] Retrying agenda generation... attempt {retry_state.attempt_number}"),
    )
    async def generate(
        self,
        documents: List[str],
        meeting_type_hint: Optional[str] = None,
        custom_prompt: Optional[str] = None,
        meeting_metadata: Optional[dict] = None,
    ) -> str:
        """
        Generate meeting agenda from documents.

        Args:
            documents: List of document texts from indexed files
            meeting_type_hint: Type hint for meeting (business, technical, brainstorming, etc.)
            custom_prompt: Custom instructions for agenda generation
            meeting_metadata: Meeting context (title, date, creator, status, projects, etc.)

        Returns:
            Generated agenda in Markdown format
        """
        # Validate inputs
        if not documents:
            documents = []

        # Combine documents into context
        combined_context = "\n\n---\n\n".join([doc for doc in documents if doc and doc.strip()])

        if not combined_context or not combined_context.strip():
            return "Không đủ thông tin để tạo chương trình họp. Vui lòng cung cấp tài liệu."

        if len(combined_context) < 50:
            return "Không đủ thông tin để tạo chương trình họp. Tài liệu quá ngắn."

        # Get prompt template for agenda
        prompt = get_prompt_for_meeting_agenda(
            meeting_type=meeting_type_hint,
            custom_instructions=custom_prompt,
        )

        # Log prompt configuration
        if custom_prompt:
            print(f"[AgendaGenerator] Using custom prompt: {custom_prompt[:100]}...")
        else:
            print(f"[AgendaGenerator] Using default prompt for meeting type: {meeting_type_hint or 'general'}")

        # Build metadata section
        metadata_section = ""
        if meeting_metadata:
            metadata_lines = ["--- METADATA HỌP ---"]
            if meeting_metadata.get("title"):
                metadata_lines.append(f"Tiêu đề: {meeting_metadata['title']}")
            if meeting_metadata.get("start_time"):
                metadata_lines.append(f"Thời gian: {meeting_metadata['start_time']}")
            if meeting_metadata.get("created_by_name"):
                metadata_lines.append(f"Người tạo: {meeting_metadata['created_by_name']}")
            if meeting_metadata.get("projects"):
                projects_str = ", ".join(meeting_metadata["projects"])
                metadata_lines.append(f"Dự án: {projects_str}")
            if meeting_metadata.get("status"):
                metadata_lines.append(f"Trạng thái: {meeting_metadata['status']}")
            if metadata_lines:
                metadata_section = "\n".join(metadata_lines) + "\n\n"

        # Create full prompt with metadata and context
        full_prompt = f"{prompt}\n\n{metadata_section}--- CONTEXT FROM DOCUMENTS ---\n\n{combined_context}"

        try:
            # Call LLM to generate agenda
            run_output = await self.arun(full_prompt)

            # Extract agenda markdown from RunOutput
            if run_output and hasattr(run_output, "messages") and len(run_output.messages) > 0:
                # Get the last message which contains the response
                last_message = run_output.messages[-1]
                if hasattr(last_message, "content"):
                    content = last_message.content
                    # Extract markdown content (string)
                    if isinstance(content, str) and content.strip():
                        return content.strip()
                    # If content is a dict (shouldn't happen without structured output), try to get agenda
                    elif isinstance(content, dict) and "agenda" in content:
                        agenda_text = content["agenda"]
                        return agenda_text if isinstance(agenda_text, str) else str(agenda_text)

            return "Không thể tạo chương trình họp từ tài liệu được cung cấp."

        except Exception as e:
            print(f"[AgendaGenerator] Error generating agenda: {e}")
            raise


async def generate_agenda_from_documents(
    documents: List[str],
    model: Any,
    meeting_type_hint: Optional[str] = None,
    custom_prompt: Optional[str] = None,
    meeting_metadata: Optional[dict] = None,
) -> tuple[str, dict]:
    """
    Generate meeting agenda from documents.

    Args:
        documents: List of document texts from indexed files
        model: LLM model instance
        meeting_type_hint: Type hint for meeting
        custom_prompt: Custom instructions
        meeting_metadata: Meeting context (title, date, creator, status, projects, etc.)

    Returns:
        Tuple of (agenda_content, token_usage)
    """
    generator = AgendaGenerator(model)

    agenda = await generator.generate(
        documents=documents,
        meeting_type_hint=meeting_type_hint,
        custom_prompt=custom_prompt,
        meeting_metadata=meeting_metadata,
    )

    # Token usage from model (if available)
    token_usage = {}
    if hasattr(generator, "model") and hasattr(generator.model, "token_usage"):
        token_usage = generator.model.token_usage

    return agenda, token_usage
