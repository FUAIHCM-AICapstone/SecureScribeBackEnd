from __future__ import annotations

from typing import Callable, Dict, Optional
from uuid import UUID

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, Transcript
from app.schemas.meeting import MeetingCreate
from app.schemas.transcript import TranscriptCreate
from app.services import meeting_note as meeting_note_service
from app.services.meeting import create_meeting
from app.services.meeting_note import delete_meeting_note
from app.services.transcript import create_transcript

VIETNAMESE_TRANSCRIPT = "Chào mọi người, cảm ơn tất cả đã có mặt hôm nay. Mục tiêu chính của chúng ta là xem xét tiến độ dự án phát triển ứng dụng mới và phân công nhiệm vụ cho tuần tới. Anna, bạn có thể cập nhật tình hình phát triển giao diện người dùng không? Vâng, John. Hiện tại, giao diện người dùng đã hoàn thành khoảng 70%. Chúng tôi đã xong phần thiết kế chính và đang thử nghiệm tính năng đăng nhập. Tuy nhiên, có một vấn đề nhỏ với tốc độ tải trang trên thiết bị di động. Tôi đề xuất dành thêm thời gian để tối ưu hóa. Tôi có thể hỗ trợ kiểm tra hiệu suất từ phía backend nếu cần. Tuần này, nhóm backend đã hoàn thành API đăng nhập và bắt đầu làm API thanh toán. Chúng tôi cần nhóm giao diện cung cấp thêm thông tin về định dạng dữ liệu mong muốn. Tuyệt vời, cảm ơn cả hai. Vậy chúng ta thống nhất nhé: Anna sẽ dẫn đầu việc tối ưu hóa giao diện di động, và Mike sẽ phối hợp để đảm bảo API phù hợp. Có câu hỏi nào về nhiệm vụ này không? Tôi muốn hỏi, liệu chúng ta có nên ưu tiên tính năng thanh toán trước hay tiếp tục với giao diện chính? Tốt, câu hỏi hay. Tôi nghĩ chúng ta nên ưu tiên giao diện chính để đảm bảo trải nghiệm người dùng mượt mà, sau đó mới tập trung vào thanh toán. Mọi người thấy ổn không? Đồng ý. Tôi sẽ lên kế hoạch để hoàn thành API thanh toán trong tuần sau. OK, vậy tuần tới Anna tập trung tối ưu giao diện, Mike hoàn thiện API thanh toán. Tôi sẽ gửi email tóm tắt các nhiệm vụ này. Có ý kiến gì thêm không? (Im lặng) Tốt, cảm ơn mọi người, chúng ta kết thúc tại đây."

DEFAULT_SUMMARY = {
    "content": "Tóm tắt truyền thống",
    "summaries": {"Objective": "Tóm tắt truyền thống"},
    "sections": ["Objective"],
}


@pytest.fixture()
def meeting_factory(db: Session, test_user) -> Callable[[Optional[str]], UUID]:
    created: list[Meeting] = []

    def _factory(transcript: Optional[str]) -> UUID:
        meeting = create_meeting(
            db,
            MeetingCreate(title="Kế hoạch tuần", description="Họp cập nhật tiến độ"),
            test_user.id,
        )
        if transcript is not None:
            create_transcript(
                db,
                TranscriptCreate(meeting_id=meeting.id, content=transcript),
            )
        created.append(meeting)
        return meeting.id

    yield _factory

    for meeting in created:
        note = meeting_note_service._get_note(db, meeting.id)
        if note is not None:
            db.delete(note)
        transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting.id).first()
        if transcript is not None:
            db.delete(transcript)
        reloaded = db.query(Meeting).get(meeting.id)
        if reloaded is not None:
            db.delete(reloaded)
    db.commit()


def _fake_summary(monkeypatch: pytest.MonkeyPatch, summary: Dict[str, object] = DEFAULT_SUMMARY) -> None:
    async def _stub(*args, **kwargs):  # noqa: D401
        return summary

    monkeypatch.setattr(meeting_note_service, "generate_meeting_summary", _stub)


@pytest.mark.asyncio
async def test_create_meeting_note_ai_success(db: Session, test_user, meeting_factory, monkeypatch):
    """Đảm bảo AI tạo ghi chú đầy đủ khi hoạt động bình thường."""
    meeting_id = meeting_factory(VIETNAMESE_TRANSCRIPT)

    class SuccessfulAnalyzer:
        async def complete(self, transcript, meeting_type=None, custom_prompt=None):  # noqa: D401
            return {
                "meeting_note": "# Ghi chú - Quyết định rõ ràng",
                "is_informative": True,
                "meeting_type": "general",
            }

    _fake_summary(monkeypatch)
    monkeypatch.setattr(meeting_note_service, "_MEETING_ANALYZER", SuccessfulAnalyzer())

    result = await meeting_note_service.create_meeting_note(db, meeting_id, test_user.id)

    assert result["content"] == "# Ghi chú - Quyết định rõ ràng"
    note = meeting_note_service.get_meeting_note(db, meeting_id, test_user.id)
    assert note.content == "# Ghi chú - Quyết định rõ ràng"


@pytest.mark.asyncio
async def test_create_meeting_note_non_informative(db: Session, test_user, meeting_factory, monkeypatch):
    """Đảm bảo transcript quá ngắn sẽ dùng tóm tắt truyền thống."""
    meeting_id = meeting_factory("Xin chào.")

    class NonInformativeAnalyzer:
        async def complete(self, transcript, meeting_type=None, custom_prompt=None):  # noqa: D401
            return {"meeting_note": "", "is_informative": False, "meeting_type": "general"}

    _fake_summary(monkeypatch)
    monkeypatch.setattr(meeting_note_service, "_MEETING_ANALYZER", NonInformativeAnalyzer())

    result = await meeting_note_service.create_meeting_note(db, meeting_id, test_user.id)
    assert result["content"] == "Tóm tắt truyền thống"


@pytest.mark.asyncio
async def test_create_meeting_note_ai_disabled(db: Session, test_user, meeting_factory, monkeypatch):
    """Đảm bảo khi tắt AI thì luôn dùng tóm tắt cũ."""
    meeting_id = meeting_factory(VIETNAMESE_TRANSCRIPT)

    class ExplodingAnalyzer:
        async def complete(self, *args, **kwargs):  # noqa: D401
            raise RuntimeError("Không được gọi")

    _fake_summary(monkeypatch)
    monkeypatch.setattr(meeting_note_service, "_MEETING_ANALYZER", ExplodingAnalyzer())

    result = await meeting_note_service.create_meeting_note(
        db,
        meeting_id,
        test_user.id,
        use_ai=False,
    )

    assert result["content"] == "Tóm tắt truyền thống"


@pytest.mark.asyncio
async def test_create_meeting_note_missing_transcript(db: Session, test_user, meeting_factory, monkeypatch):
    """Đảm bảo thiếu transcript sẽ fallback sang tóm tắt truyền thống (không raise lỗi)."""
    meeting_id = meeting_factory(None)
    _fake_summary(monkeypatch)

    result = await meeting_note_service.create_meeting_note(db, meeting_id, test_user.id)
    assert result["content"] == "Tóm tắt truyền thống"


@pytest.mark.asyncio
async def test_update_meeting_note_manual_edit(db: Session, test_user, meeting_factory, monkeypatch):
    meeting_id = meeting_factory(None)
    meeting_note_service.upsert_meeting_note(db, meeting_id, test_user.id, "Initial content")

    async def _raise(*args, **kwargs):
        raise AssertionError("generate_meeting_summary should not run during manual update")

    monkeypatch.setattr(meeting_note_service, "generate_meeting_summary", _raise)

    updated = await meeting_note_service.update_meeting_note(
        db,
        meeting_id,
        test_user.id,
        content="Manual update",
    )

    assert updated.content == "Manual update"
    note = meeting_note_service.get_meeting_note(db, meeting_id, test_user.id)
    assert note.content == "Manual update"
