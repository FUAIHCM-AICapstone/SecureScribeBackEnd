"""Sliding window extraction for large document processing."""

from typing import List, Tuple, Dict, Any

from app.utils.llm import chat_complete


async def extract_important_notes_from_chunk(
    chunk_text: str,
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Extract important notes from a single document chunk with token tracking.

    Args:
        chunk_text: Text content of a single document chunk

    Returns:
        Tuple of (list of important notes, token usage dict with input/output tokens)
    """
    if not chunk_text or len(chunk_text.strip()) < 50:
        return [], {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    system_prompt = """Bạn là trợ lý phân tích tài liệu chuyên nghiệp. 
Hãy trích xuất TOÀN BỘ thông tin quan trọng từ đoạn văn bản được cung cấp dưới dạng danh sách chi tiết.

HƯỚNG DẪN TRÍCH XUẤT:
1. Mục tiêu/Vấn đề được thảo luận
2. Các quyết định/kết luận được đưa ra
3. Hành động/nhiệm vụ được giao
4. Người chịu trách nhiệm (nếu có)
5. Deadline/Thời hạn (nếu có)
6. Các con số, thống kê quan trọng
7. Kết quả, đầu ra dự kiến
8. Rủi ro hoặc vấn đề còn tồn đọng
9. Tài liệu/Tham chiếu liên quan
10. Bất kỳ thông tin nào khác có giá trị

FORMAT TRÍCH XUẤT:
- Mỗi mục trên một dòng riêng
- Bắt đầu bằng "- " cho mỗi mục
- Viết đầy đủ, chi tiết nhưng ngắn gọn
- CHỈ trích xuất những gì THỰC TỀ từ văn bản, không sáng tạo thông tin mới
- Nếu không có thông tin nào quan trọng, trả về danh sách trống"""

    user_prompt = f"""Hãy trích xuất toàn bộ thông tin quan trọng từ đoạn văn bản sau:\n\n{chunk_text}"""

    try:
        response = await chat_complete(system_prompt, user_prompt)

        if not response:
            return [], {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        notes = [
            line.strip()
            for line in response.strip().split("\n")
            if line.strip() and len(line.strip()) > 5
        ]

        # Estimate token usage (rough approximation)
        # Gemini uses ~4 chars per token on average
        input_tokens = len((system_prompt + user_prompt) or "") // 4
        output_tokens = len(response or "") // 4
        total_tokens = input_tokens + output_tokens

        token_usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

        return notes, token_usage

    except Exception as e:
        print(f"[SLIDING WINDOW] Error extracting notes from chunk: {e}")
        return [], {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
