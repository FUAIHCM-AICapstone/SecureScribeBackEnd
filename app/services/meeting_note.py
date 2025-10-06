from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.meeting import MeetingNote
from app.services.meeting import get_meeting
from app.services.transcript import get_transcript_by_meeting
from app.utils.meeting_agent import MeetingAnalyzer
from app.utils.meeting_summary import generate_meeting_summary

LOGGER = logging.getLogger(__name__)

try:
    _MEETING_ANALYZER = MeetingAnalyzer()
except Exception as exc:  # pragma: no cover - defensive
    LOGGER.warning("MeetingAnalyzer initialisation failed: %s", exc)
    _MEETING_ANALYZER = None


def _get_note(db: Session, meeting_id: UUID) -> Optional[MeetingNote]:
    return db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()


def get_meeting_note(db: Session, meeting_id: UUID, user_id: UUID, *, raise_not_found: bool = True) -> Optional[MeetingNote]:
    get_meeting(db, meeting_id, user_id, raise_404=True)
    note = _get_note(db, meeting_id)
    if not note and raise_not_found:
        raise HTTPException(status_code=404, detail="Meeting note not found")
    return note


def upsert_meeting_note(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    content: str,
    *,
    ai_data: Optional[Dict[str, Any]] = None,
) -> MeetingNote:
    now = datetime.utcnow()
    note = _get_note(db, meeting_id)
    if note:
        note.content = content
        note.last_editor_id = user_id
        note.last_edited_at = now
    else:
        note = MeetingNote(
            meeting_id=meeting_id,
            content=content,
            last_editor_id=user_id,
            last_edited_at=now,
        )
        db.add(note)

    # if ai_data:
    #     note.ai_meeting_type = ai_data.get('meeting_type')
    #     note.ai_is_informative = ai_data.get('is_informative')
    #     note.ai_task_items = ai_data.get('task_items') or []
    #     note.ai_decision_items = ai_data.get('decision_items') or []
    #     note.ai_question_items = ai_data.get('question_items') or []
    #     note.ai_token_usage = ai_data.get('token_usage') or {}
    # else:
    #     note.ai_meeting_type = None
    #     note.ai_is_informative = None
    #     note.ai_task_items = []
    #     note.ai_decision_items = []
    #     note.ai_question_items = []
    #     note.ai_token_usage = {}
    db.commit()
    db.refresh(note)
    return note


async def create_meeting_note(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    *,
    use_ai: bool = True,
    custom_prompt: Optional[str] = None,
    meeting_type_hint: Optional[str] = None,
) -> Dict[str, object]:
    get_meeting(db, meeting_id, user_id, raise_404=True)
    existing = _get_note(db, meeting_id)
    if existing:
        raise HTTPException(status_code=409, detail="Meeting note already exists")

    summary = await generate_meeting_summary(db, meeting_id, user_id)
    summary_content: str = summary["content"]  # type: ignore[assignment]
    summaries = summary["summaries"]  # type: ignore[assignment]
    sections = summary["sections"]  # type: ignore[assignment]

    # ai_payload: Optional[Dict[str, Any]] = None
    ai_note_content: Optional[str] = None

    transcript = get_transcript_by_meeting(db, meeting_id)
    transcript_content = transcript.content if transcript else None

    if use_ai and _MEETING_ANALYZER and transcript_content:
        try:
            ai_result = await _MEETING_ANALYZER.complete(
                transcript=transcript_content,
                meeting_type=meeting_type_hint,
                custom_prompt=custom_prompt,
            )
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.error("MeetingAnalyzer execution failed: %s", exc, exc_info=True)
        else:
            is_informative = bool(ai_result.get("is_informative", True))
            meeting_note = (ai_result.get("meeting_note") or "").strip()
            if is_informative and meeting_note:
                # ai_payload = {
                #     'meeting_type': ai_result.get('meeting_type')
                #     'is_informative': is_informative
                #     'task_items': ai_result.get('task_items') or []
                #     'decision_items': ai_result.get('decision_items') or []
                #     'question_items': ai_result.get('question_items') or []
                #     'token_usage': ai_result.get('token_usage') or {}
                ai_note_content = meeting_note
                # }
            else:
                LOGGER.info("MeetingAnalyzer returned insufficient data; falling back to summary")

    note_content = ai_note_content or summary_content
    note = upsert_meeting_note(db, meeting_id, user_id, note_content)

    return {
        "note": note,
        "content": note_content,
        "summaries": summaries,
        "sections": sections,
        # "ai": ai_payload,
    }


async def update_meeting_note(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    *,
    content: str,
) -> MeetingNote:
    get_meeting_note(db, meeting_id, user_id)
    return upsert_meeting_note(db, meeting_id, user_id, content)


def delete_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> None:
    note = get_meeting_note(db, meeting_id, user_id)
    db.delete(note)
    db.commit()