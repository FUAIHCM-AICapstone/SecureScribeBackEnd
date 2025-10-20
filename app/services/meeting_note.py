import asyncio
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.meeting import MeetingNote
from app.services.meeting import get_meeting
from app.services.transcript import get_transcript_by_meeting
from app.utils.meeting_agent import MeetingAnalyzer


def get_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> Optional[MeetingNote]:
    get_meeting(db, meeting_id, user_id, raise_404=True)
    note = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
    return note


def create_meeting_note(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    custom_prompt: Optional[str] = None,
    meeting_type_hint: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    get_meeting(db, meeting_id, user_id, raise_404=True)

    existing = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
    if existing:
        return None

    transcript = get_transcript_by_meeting(db, meeting_id)
    if not transcript or not transcript.content:
        return None

    ai_result = generate_meeting_note_content(
        transcript.content,
        meeting_type_hint=meeting_type_hint,
        custom_prompt=custom_prompt,
    )

    if not ai_result.get("content"):
        return None

    note = MeetingNote(meeting_id=meeting_id, content=ai_result["content"], last_editor_id=user_id, last_edited_at=datetime.utcnow())

    db.add(note)
    db.commit()
    db.refresh(note)

    return {
        "note": note,
        "content": ai_result["content"],
        "task_items": ai_result.get("task_items", []),
        "decision_items": ai_result.get("decision_items", []),
        "question_items": ai_result.get("question_items", []),
        "token_usage": ai_result.get("token_usage", {}),
    }


def generate_meeting_note_content(
    transcript_content: str,
    meeting_type_hint: Optional[str] = None,
    custom_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate meeting note content using AI agent"""
    try:
        analyzer = MeetingAnalyzer()
        result = asyncio.run(
            analyzer.complete(
                transcript=transcript_content,
                meeting_type=meeting_type_hint,
                custom_prompt=custom_prompt,
            )
        )

        is_informative = bool(result.get("is_informative", True))
        meeting_note = (result.get("meeting_note") or "").strip()

        if is_informative and meeting_note:
            return {
                "content": meeting_note,
                "task_items": result.get("task_items", []),
                "decision_items": result.get("decision_items", []),
                "question_items": result.get("question_items", []),
                "token_usage": result.get("token_usage", {}),
            }

    except Exception:
        pass

    return {
        "content": "",
        "task_items": [],
        "decision_items": [],
        "question_items": [],
        "token_usage": {},
    }


def update_meeting_note(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    content: str,
) -> Optional[MeetingNote]:
    note = get_meeting_note(db, meeting_id, user_id)
    if not note:
        return None
    note.content = content
    note.last_editor_id = user_id
    note.last_edited_at = datetime.utcnow()
    db.commit()
    db.refresh(note)
    return note


def delete_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> bool:
    note = get_meeting_note(db, meeting_id, user_id)
    if not note:
        return False
    db.delete(note)
    db.commit()
    return True
