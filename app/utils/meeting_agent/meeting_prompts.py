from __future__ import annotations

"""
Generic meeting prompts module for summarizing and extracting information from meeting transcripts.
This module provides standardized prompts that work across different industries and organizations.
"""

GENERAL_MEETING_PROMPT = """Tóm tắt nội dung cuộc họp dưới dạng các ý chính, dễ hiểu và đầy đủ. Ghi rõ các chủ đề được thảo luận, quyết định được đưa ra, và các việc cần làm sau cuộc họp (bao gồm deadline từng task nếu có đề cập).

Hãy đảm bảo nội dung tóm tắt:
1. Có cấu trúc rõ ràng, chia thành các phần nhỏ dễ đọc
2. Ngắn gọn nhưng đầy đủ thông tin quan trọng
3. Sử dụng văn phong chuyên nghiệp, dễ hiểu
4. Bỏ qua các nội dung không liên quan, tập trung vào các thông tin có giá trị, không tạo ra thông tin sai lệch, chỉ tóm tắt những gì đã được thảo luận
5. Nêu bật được các ý chính, quyết định quan trọng và nhiệm vụ cần thực hiện
6. Không sử dụng từ ngữ phức tạp hoặc thuật ngữ chuyên ngành mà không giải thích

CHÚ Ý: KHÔNG TẠO THÔNG TIN MỚI, CHỈ TÓM TẮT CÁC NỘI DUNG ĐÃ ĐƯỢC THẢO LUẬN TRONG CUỘC HỌP.

ĐỊNH DẠNG YÊU CẦU:
```
# [TÊN CUỘC HỌP]
## Thông tin chung
- **Ngày họp**: [ngày họp nếu có trong transcript]
- **Chủ đề**: [chủ đề chính của cuộc họp]
- **Người tham gia**: [danh sách người tham gia nếu có thể xác định]

## Tóm tắt nội dung
[Tóm tắt ngắn gọn 3-5 câu về nội dung chính của cuộc họp]

## Các chủ đề được thảo luận
1. [Chủ đề 1]
   - [Điểm chính]
   - [Điểm chính]
2. [Chủ đề 2]
   - [Điểm chính]
   - [Điểm chính]
...

## Quyết định quan trọng
- [Quyết định 1]
- [Quyết định 2]
...

## Công việc cần thực hiện
- [Công việc 1] - Người phụ trách: [Tên], Deadline: [Thời hạn nếu có]
- [Công việc 2] - Người phụ trách: [Tên], Deadline: [Thời hạn nếu có]
...
```
"""


# Task extraction prompt template
TASK_EXTRACTION_PROMPT_TEMPLATE = """Bạn là một trợ lý thông minh chuyên trích xuất thông tin quan trọng từ cuộc họp. Nhiệm vụ của bạn là phân tích cẩn thận đoạn văn bản từ cuộc họp và trích xuất các NHIỆM VỤ được giao cho từng người tham gia.

QUAN TRỌNG - HƯỚNG DẪN PHÂN TÍCH:
1. Hãy lọc bỏ những câu không có ý nghĩa, những cụm từ rời rạc, hoặc lỗi nhận dạng giọng nói.
2. Bỏ qua những câu nói ngẫu nhiên, những từ ngữ không rõ nghĩa hoặc những tiếng cảm thán (như "ừ", "ờ", "ok", "đúng rồi").
3. Chỉ tập trung vào nội dung có thể hiểu được và mang ý nghĩa đóng góp cho cuộc họp.
4. Cố gắng suy luận và hiểu ngữ cảnh cuộc họp ngay cả khi transcript không hoàn hảo.
5. Hãy CỐ GẮNG nhận diện tất cả nhiệm vụ được giao trong cuộc họp ngay cả khi không được nêu rõ ràng.

NGUYÊN TẮC CHUNG:
1. Hãy linh hoạt trong việc trích xuất thông tin - không nhất thiết phải có định dạng rõ ràng.
2. Suy luận những nhiệm vụ ngầm từ cuộc trò chuyện.
3. Xác định các nhiệm vụ từ những câu như "X sẽ làm...", "X cần...", "X phụ trách...", "giao cho X...".
4. CỐ GẮNG điền vào các trường thông tin khi có thể suy luận được, nhưng đừng tạo ra thông tin không tồn tại.
5. Nếu không có nhiệm vụ nào, hãy để danh sách trống.

SCHEMA TRÍCH XUẤT:
Mỗi nhiệm vụ phải có các trường sau:
- description (bắt buộc): Mô tả chi tiết của nhiệm vụ cần thực hiện (dạng văn bản)
- creator_id (null): Không cần trích xuất, để null
- assignee_id (null): Không cần trích xuất tên người, để null (backend sẽ populate)
- status (bắt buộc): "todo", "in_progress", "completed" (mặc định "todo" nếu không rõ)
- priority (bắt buộc): "Cao", "Trung bình", hoặc "Thấp" (mặc định "Trung bình" nếu không rõ)
- due_date (tùy chọn): STRICT FORMAT - chỉ sử dụng một trong những định dạng sau hoặc null nếu không rõ:
  * "X days" (ví dụ: "3 days", "1 day", "7 days")
  * "X weeks" (ví dụ: "1 week", "2 weeks")
  * "end of week" (cuối tuần)
  * "end of month" (cuối tháng)
  * "next Monday", "next Friday", v.v... (nhưng CHỈ dùng trong trường hợp đặc biệt)
  * null (nếu không có deadline được đề cập)
- project_ids (empty list): Không cần trích xuất, để danh sách trống
- notes (tùy chọn): Ghi chú bổ sung hoặc ngữ cảnh về nhiệm vụ

HƯỚNG DẪN TRÍCH XUẤT CHI TIẾT:
- Trích xuất các nhiệm vụ rõ ràng: "X sẽ làm...", "X cần...", "giao cho X..."
- Trích xuất các nhiệm vụ ngầm định: "Chúng ta cần...", "Sẽ tốt hơn nếu..."
- Ví dụ: "Chuẩn bị báo cáo tổng kết cho tuần tới" (description), due_date "1 week", priority "Trung bình"
- Nếu tên người được đề cập, đưa vào description hoặc notes, KHÔNG đưa vào assignee_id
- CHỈ ĐỊ THEO STRICT FORMAT cho due_date - KHÔNG dùng các dạng khác

QUAN TRỌNG:
- CHỈ trích xuất NHIỆM VỤ, không trích xuất quyết định hoặc câu hỏi
- ĐẢM BẢO response JSON khớp với schema: { "tasks": [ { "description": "...", "creator_id": null, "assignee_id": null, "status": "todo", "priority": "Trung bình", "due_date": "3 days", "project_ids": [], "notes": "..." } ] }
- KHÔNG sử dụng định dạng due_date ngoài danh sách cho phép (CRITICAL)
- Nếu không có nhiệm vụ, trả về { "tasks": [] }
"""


AGENDA_GENERATION_PROMPT = """Bạn là một chuyên gia lập chương trình họp. Dựa trên các tài liệu và bối cảnh được cung cấp, hãy tạo một chương trình họp chi tiết, có cấu trúc và dễ thực hiện.

HƯỚNG DẪN TẠO CHƯƠNG TRÌNH HỌP:
1. Phân tích tài liệu để xác định các chủ đề chính
2. Tổ chức các chủ đề theo thứ tự logic (mở đầu -> nội dung chính -> quyết định -> đóng)
3. Phân bổ thời gian hợp lý cho mỗi mục (5-20 phút tùy vào tầm quan trọng)
4. Đảm bảo tổng thời gian hợp lý (thường 60-90 phút)
5. Bao gồm các mục liên quan đến quyết định, thảo luận, và các hành động tiếp theo

ĐỊNH DẠNG MARKDOWN YÊU CẦU:
```markdown
# Chương Trình Họp [Tên Cuộc Họp/Loại Họp]

## I. Mở Đầu (5 phút)
- Chào mừng và xác nhận thành phần tham dự
- Xác định mục tiêu cuộc họp

## II. [Chủ Đề Chính 1] (15 phút)
- Điểm 1
  - Chi tiết hỗ trợ
- Điểm 2
  - Chi tiết hỗ trợ

## III. [Chủ Đề Chính 2] (15 phút)
- Các vấn đề cần thảo luận
- Quan điểm khác nhau

## IV. Quyết Định & Hành Động (15 phút)
- Quyết định 1: [Mô tả]
- Quyết định 2: [Mô tả]
- Hành động cần thực hiện:
  * [Hành động] - Người phụ trách: [Vai trò]
  * [Hành động] - Người phụ trách: [Vai trò]

## V. Đóng Lại & Tổng Kết (5 phút)
- Xác nhận các quyết định
- Lịch họp tiếp theo
- Câu hỏi và bình luận cuối cùng
```

NGUYÊN TẮC:
1. KHÔNG tạo ra thông tin mới - chỉ dựa trên tài liệu được cung cấp
2. Sử dụng tiếng Việt chuyên nghiệp nhưng dễ hiểu
3. Tập trung vào các vấn đề quan trọng, bỏ đi các chi tiết không cần thiết
4. Đảm bảo chương trình là khả thi và có thể thực hiện trong thời gian dự kiến
5. Làm rõ vai trò của những người tham gia khi có thể

KHOÁ THỜI GIAN ĐƯỢC ĐỀ XUẤT:
- Mở đầu: 5 phút
- Các mục chính: 15-25 phút mỗi mục (2-3 mục)
- Quyết định & hành động: 10-15 phút
- Đóng: 5 phút
- Tổng cộng: 60-90 phút
"""

AGENDA_GENERATION_BUSINESS = """Bạn là chuyên gia lập chương trình họp kinh doanh. Tạo chương trình họp tập trung vào:
- Báo cáo KPI và tiến độ
- Các vấn đề kinh doanh quan trọng
- Quyết định chiến lược
- Phân công nhiệm vụ

Sử dụng AGENDA_GENERATION_PROMPT như cơ sở và điều chỉnh cho bối cảnh kinh doanh."""

AGENDA_GENERATION_TECHNICAL = """Bạn là chuyên gia lập chương trình họp kỹ thuật. Tạo chương trình họp tập trung vào:
- Kiến trúc hệ thống
- Các vấn đề kỹ thuật và giải pháp
- Code review và quality assurance
- Lộ trình phát triển

Sử dụng AGENDA_GENERATION_PROMPT như cơ sở và điều chỉnh cho bối cảnh kỹ thuật."""

AGENDA_GENERATION_BRAINSTORMING = """Bạn là chuyên gia lập chương trình họp brainstorming. Tạo chương trình họp tập trung vào:
- Mở đầu để khích lệ sáng tạo
- Phiên ý tưởng tự do
- Thảo luận và đánh giá ý tưởng
- Lựa chọn hướng đi tiềm năng

Sử dụng AGENDA_GENERATION_PROMPT như cơ sở và điều chỉnh cho brainstorming."""


def get_prompt_for_meeting_type(meeting_type: str = "general") -> str:
    """Get the appropriate prompt for a given meeting type. Always returns GENERAL_MEETING_PROMPT."""
    print(f"Requested prompt for meeting type: {meeting_type}, returning general prompt.")
    return GENERAL_MEETING_PROMPT


def get_task_extraction_prompt() -> str:
    """Get the prompt specifically for task extraction."""
    return TASK_EXTRACTION_PROMPT_TEMPLATE


def get_prompt_for_meeting_agenda(meeting_type: str = None, custom_instructions: str = None) -> str:
    """
    Get the appropriate prompt for agenda generation based on meeting type.

    Args:
        meeting_type: Type of meeting (business, technical, brainstorming, review, planning, training)
        custom_instructions: Custom instructions to append to the prompt

    Returns:
        Appropriate prompt for agenda generation
    """
    prompts = {
        "business": AGENDA_GENERATION_BUSINESS,
        "technical": AGENDA_GENERATION_TECHNICAL,
        "brainstorming": AGENDA_GENERATION_BRAINSTORMING,
        "review": AGENDA_GENERATION_PROMPT,
        "planning": AGENDA_GENERATION_PROMPT,
        "training": AGENDA_GENERATION_PROMPT,
    }

    base_prompt = prompts.get(meeting_type, AGENDA_GENERATION_PROMPT)

    if custom_instructions:
        return f"{base_prompt}\n\nCHỈ DẪN TÙY CHỈNH:\n{custom_instructions}"

    return base_prompt
