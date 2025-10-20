from datetime import datetime
from typing import Dict, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.meeting import MeetingNote
from app.services.meeting import get_meeting
from app.utils.meeting_summary import generate_meeting_summary, normalize_summary_sections


def get_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> MeetingNote:
    get_meeting(db, meeting_id, user_id, raise_404=True)
    note = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting note not found")
    return note


def create_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> MeetingNote:
    get_meeting(db, meeting_id, user_id, raise_404=True)
    existing = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Meeting note already exists")
    now = datetime.utcnow()
    summary = generate_meeting_summary(db, meeting_id, user_id)
    content: str = summary["content"]
    note = MeetingNote(meeting_id=meeting_id, content=content, last_editor_id=user_id, last_edited_at=now)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def update_meeting_note(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    *,
    content: Optional[str] = None,
    sections: Optional[Sequence[str]] = None,
) -> MeetingNote:
    note = get_meeting_note(db, meeting_id, user_id)
    now = datetime.utcnow()
    materialized = content
    if materialized is None:
        normalized = normalize_summary_sections(sections)
        summary = generate_meeting_summary(db, meeting_id, user_id, normalized)
        materialized = summary["content"]
    note.content = materialized
    note.last_editor_id = user_id
    note.last_edited_at = now
    db.commit()
    db.refresh(note)
    return note


def delete_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> None:
    note = get_meeting_note(db, meeting_id, user_id)
    db.delete(note)
    db.commit()


def summarize_meeting_sections_for_chat(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    sections: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    get_meeting(db, meeting_id, user_id, raise_404=True)
    result = generate_meeting_summary(db, meeting_id, user_id, sections)
    return {
        "content": result["content"],
        "summaries": result["summaries"],
        "sections": result["sections"],
    }
