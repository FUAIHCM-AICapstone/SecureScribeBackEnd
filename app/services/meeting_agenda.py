from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.crud.meeting_agenda import crud_create_meeting_agenda, crud_delete_meeting_agenda, crud_get_meeting_agenda, crud_update_meeting_agenda
from app.events.domain_events import BaseDomainEvent
from app.schemas.meeting_agenda import MeetingAgendaGenerateResponse
from app.services.event_manager import EventManager
from app.services.meeting import get_meeting


def get_meeting_agenda(db: Session, meeting_id: UUID, user_id: UUID) -> Optional[Any]:
    get_meeting(db, meeting_id, user_id, raise_404=True)
    return crud_get_meeting_agenda(db, meeting_id)


def create_meeting_agenda(db: Session, meeting_id: UUID, user_id: UUID, content: str) -> Optional[Any]:
    existing_agenda = crud_get_meeting_agenda(db, meeting_id)
    if existing_agenda:
        return update_meeting_agenda(db, meeting_id, user_id, content)
    get_meeting(db, meeting_id, user_id, raise_404=True)
    agenda = crud_create_meeting_agenda(db, meeting_id, content, user_id)
    EventManager.emit_domain_event(BaseDomainEvent(event_name="meeting_agenda.created", actor_user_id=user_id, target_type="meeting_agenda", target_id=meeting_id, metadata={"content_length": len(agenda.content) if agenda.content else 0}))
    return agenda


def update_meeting_agenda(db: Session, meeting_id: UUID, user_id: UUID, content: str) -> Optional[Any]:
    agenda = get_meeting_agenda(db, meeting_id, user_id)
    if not agenda:
        return None
    original_content = agenda.content
    agenda = crud_update_meeting_agenda(db, meeting_id, content, user_id)
    if original_content != agenda.content:
        EventManager.emit_domain_event(BaseDomainEvent(event_name="meeting_agenda.updated", actor_user_id=user_id, target_type="meeting_agenda", target_id=meeting_id, metadata={"diff": {"content": [original_content, agenda.content]}}))
    return agenda


def delete_meeting_agenda(db: Session, meeting_id: UUID, user_id: UUID) -> bool:
    agenda = get_meeting_agenda(db, meeting_id, user_id)
    if not agenda:
        return False
    if crud_delete_meeting_agenda(db, meeting_id):
        EventManager.emit_domain_event(BaseDomainEvent(event_name="meeting_agenda.deleted", actor_user_id=user_id, target_type="meeting_agenda", target_id=meeting_id, metadata={}))
        return True
    return False


def generate_meeting_agenda_with_ai(db: Session, meeting_id: UUID, user_id: UUID, custom_prompt: Optional[str] = None, meeting_type_hint: Optional[str] = None) -> MeetingAgendaGenerateResponse:
    """
    Generate meeting agenda using AI.
    For now, returns mock response. Will integrate with actual AI service later.
    """
    get_meeting(db, meeting_id, user_id, raise_404=True)

    # Mock AI response
    mock_agenda_content = """# Chương Trình Họp

## Mục Đích
Thảo luận và đưa ra quyết định chiến lược cho dự án.

## Thứ Tự Chương Trình
1. **Mở Đầu & Báo Cáo Tiến Độ** (5 phút)
   - Tóm tắt tiến độ hiện tại
   - Các vấn đề cần giải quyết

2. **Thảo Luận Chính** (20 phút)
   - Phân tích hiện trạng
   - Xác định các rủi ro tiềm ẩn
   - Brainstorm các giải pháp

3. **Đưa Ra Quyết Định** (10 phút)
   - Thống nhất hướng đi
   - Phân công nhiệm vụ

4. **Tổng Kết & Hành Động Tiếp Theo** (5 phút)
   - Xác nhận các quyết định
   - Thiết lập lịch follow-up

## Những Người Tham Gia
- Người chủ trì
- Các stakeholder chính
- Nhóm thực hiện

## Tài Liệu Tham Khảo
- Báo cáo tiến độ
- Dữ liệu phân tích"""

    mock_token_usage = {
        "prompt_tokens": 150,
        "completion_tokens": 500,
        "total_tokens": 650,
    }

    # Save or update agenda in DB
    existing_agenda = crud_get_meeting_agenda(db, meeting_id)
    if existing_agenda:
        agenda = crud_update_meeting_agenda(db, meeting_id, mock_agenda_content, user_id)
        agenda.input_tokens = mock_token_usage.get("prompt_tokens")
        agenda.output_tokens = mock_token_usage.get("completion_tokens")
        agenda.total_tokens = mock_token_usage.get("total_tokens")
        db.commit()
        db.refresh(agenda)
        EventManager.emit_domain_event(BaseDomainEvent(event_name="meeting_agenda.regenerated", actor_user_id=user_id, target_type="meeting_agenda", target_id=meeting_id, metadata={"content_length": len(agenda.content), "regenerated": True, "token_usage": mock_token_usage}))
    else:
        agenda = crud_create_meeting_agenda(db, meeting_id, mock_agenda_content, user_id)
        agenda.input_tokens = mock_token_usage.get("prompt_tokens")
        agenda.output_tokens = mock_token_usage.get("completion_tokens")
        agenda.total_tokens = mock_token_usage.get("total_tokens")
        db.commit()
        db.refresh(agenda)
        EventManager.emit_domain_event(BaseDomainEvent(event_name="meeting_agenda.generated", actor_user_id=user_id, target_type="meeting_agenda", target_id=meeting_id, metadata={"content_length": len(agenda.content), "token_usage": mock_token_usage}))

    from app.schemas.meeting_agenda import MeetingAgendaResponse

    agenda_response = MeetingAgendaResponse(
        id=str(agenda.id),
        content=agenda.content,
        last_edited_at=agenda.last_edited_at.isoformat() if agenda.last_edited_at else None,
        created_at=agenda.created_at.isoformat(),
        updated_at=agenda.updated_at.isoformat() if agenda.updated_at else None,
    )

    return MeetingAgendaGenerateResponse(
        agenda=agenda_response,
        content=mock_agenda_content,
        token_usage=mock_token_usage,
    )
