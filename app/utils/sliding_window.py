"""Sliding window extraction for large document processing."""

from typing import List, Tuple, Dict, Any, Optional

from app.utils.llm import chat_complete


async def extract_important_notes_from_chunk(
    chunk_text: str,
    existing_notes: Optional[List[str]] = None,
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Extract important notes from a single document chunk with token tracking.

    If existing_notes provided (from Qdrant cache), uses them directly without re-extraction.

    Args:
        chunk_text: Text content of a single document chunk
        existing_notes: Optional pre-extracted notes from Qdrant cache

    Returns:
        Tuple of (list of important notes, token usage dict with input/output tokens)
    """
    # Use cached notes if available (quick access, zero token cost)
    if existing_notes and len(existing_notes) > 0:
        return existing_notes, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    if not chunk_text or len(chunk_text.strip()) < 50:
        return [], {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

    system_prompt = """Bạn là trợ lý phân tích tài liệu chuyên nghiệp.
Hãy trích xuất TOÀN BỘ thông tin quan trọng từ đoạn văn bản thành MỘT DÒNG DUY NHẤT.

HƯỚNG DẪN TRÍCH XUẤT:
1. Tổng hợp toàn bộ thông tin quan trọng: mục tiêu, quyết định, hành động, deadline, con số, rủi ro, v.v.
2. Kết hợp tất cả các điểm vào MỘT câu/đoạn dài duy nhất
3. Sử dụng dấu phẩy, dấu chấm phẩy để phân tách các ý chính
4. KHÔNG bao gồm các dòng riêng biệt (no bullet points)
5. KHÔNG lặp lại thông tin
6. KHÔNG hallucinate thông tin không tồn tại trong văn bản
7. Nếu không có thông tin quan trọng nào, trả về chuỗi rỗng

OUTPUT: Một dòng duy nhất chứa tất cả thông tin quan trọng (hoặc rỗng nếu không có gì)"""

    user_prompt = f"""Trích xuất toàn bộ thông tin quan trọng từ đoạn văn bản sau thành MỘT dòng duy nhất:\n\n{chunk_text}"""

    try:
        response = await chat_complete(system_prompt, user_prompt)

        if not response:
            return [], {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        # For condensed single-line format, wrap response as single item in list
        response_clean = response.strip()
        notes = [response_clean] if response_clean and len(response_clean) > 5 else []

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
