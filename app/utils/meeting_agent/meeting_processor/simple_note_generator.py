import logging
import time
from typing import Dict

from langchain_core.messages import AIMessage, HumanMessage

from app.utils.meeting_agent.meeting_prompts import get_prompt_for_meeting_type
from app.utils.meeting_agent.utils import count_tokens


class SimpleMeetingNoteGenerator:
    """
    Creates a simple, concise meeting note tailored to the meeting type.
    This replaces the more complex chunk-based summary approach.
    """

    def __init__(self, llm, token_tracker):
        self.llm = llm
        self.token_tracker = token_tracker
        self.logger = logging.getLogger("SimpleMeetingNoteGenerator")

    def generate(self, state) -> Dict:
        """
        Generate a simple meeting note based on the transcript and meeting type.
        Uses the type-specific prompt to format the note appropriately.
        """
        self.logger.info(f"Generating simple meeting note for meeting type: {state.get('meeting_type', 'general')}")

        meeting_type = state.get("meeting_type", "general")
        transcript = state.get("transcript", "")
        custom_prompt = state.get("custom_prompt")
        if custom_prompt:
            self.logger.info(f"Using custom prompt for meeting note generation of type '{meeting_type} custom prompt: {custom_prompt}'")
        else:
            self.logger.info("Using default prompt for meeting note generation")
        if not transcript or len(transcript) < 50:
            self.logger.warning("Transcript too short to generate meaningful meeting note")
            return {
                **state,
                "meeting_note": "Không đủ thông tin để tạo ghi chú cuộc họp.",
                "messages": state["messages"] + [HumanMessage(content="Tạo ghi chú cuộc họp"), AIMessage(content="Không đủ thông tin để tạo ghi chú cuộc họp.")],
            }

        meeting_note_prompt = get_prompt_for_meeting_type(meeting_type)

        # Create the full prompt with transcript context
        # Prioritize custom prompt if available, otherwise use the default
        base_prompt = meeting_note_prompt
        if custom_prompt:
            base_prompt = f"{meeting_note_prompt}\n\nYêu cầu đặc biệt từ người dùng (ưu tiên cao nhất):\n{custom_prompt}"

        prompt = f"""{base_prompt}

    Dưới đây là transcript cuộc họp để bạn tham khảo:

    {transcript}

    Hãy tạo một ghi chú cuộc họp ngắn gọn, rõ ràng dựa trên nội dung transcript trên.
    Lưu ý: Nếu có yêu cầu đặc biệt từ người dùng, hãy ưu tiên tuân theo các yêu cầu đó trước tiên.
    Cố gắng xác định tên người nói dựa vào nội dung cuộc họp không nên dựa vào SPEAKER ID, và danh sách người tham gia là những người đang nói trong cuộc họp, khác với những người được đề cập trong nội dung cuộc họp.
    Nếu không thể xác định tên người nói, hãy sử dụng 'Người nói' làm tên mặc định.
    """

        try:
            # Track token usage
            input_tokens = count_tokens(prompt, "gemini")
            self.token_tracker.add_input_tokens(input_tokens)

            # Start timing
            start_time = time.time()

            # Call LLM to generate meeting note
            response = self.llm.invoke(prompt)
            meeting_note = response.content

            # Track output tokens
            output_tokens = count_tokens(meeting_note, "gemini")
            self.token_tracker.add_output_tokens(output_tokens)

            # Log performance
            duration = time.time() - start_time
            self.logger.info(f"Generated meeting note in {duration:.2f} seconds")
            self.logger.info(f"Meeting note length: {len(meeting_note)} characters")

            # Update state with new meeting note
            return {
                **state,
                "meeting_note": meeting_note.replace("```", "").strip(),
                "messages": state["messages"] + [HumanMessage(content="Tạo ghi chú cuộc họp"), AIMessage(content=f"Đã tạo ghi chú cuộc họp cho loại '{meeting_type}'")],
            }

        except Exception as e:
            self.logger.error(f"Error generating meeting note: {str(e)}")
            return {
                **state,
                "meeting_note": "Đã xảy ra lỗi khi tạo ghi chú cuộc họp.",
                "messages": state["messages"] + [HumanMessage(content="Tạo ghi chú cuộc họp"), AIMessage(content=f"Lỗi: {str(e)}")],
            }
