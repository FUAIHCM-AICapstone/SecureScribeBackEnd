from datetime import datetime
from typing import Dict, Optional, Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.meeting import MeetingNote
from app.services.meeting import get_meeting
from app.utils.meeting_summary import generate_meeting_summary, normalize_summary_sections


def _get_note(db: Session, meeting_id: UUID) -> Optional[MeetingNote]:
    return db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()


def get_meeting_note(db: Session, meeting_id: UUID, user_id: UUID, *, raise_not_found: bool = True) -> Optional[MeetingNote]:
    get_meeting(db, meeting_id, user_id, raise_404=True)
    note = _get_note(db, meeting_id)
    if not note and raise_not_found:
        raise HTTPException(status_code=404, detail="Meeting note not found")
    return note


def upsert_meeting_note(db: Session, meeting_id: UUID, user_id: UUID, content: str) -> MeetingNote:
    now = datetime.utcnow()
    note = _get_note(db, meeting_id)
    if note:
        note.content = content
        note.last_editor_id = user_id
        note.last_edited_at = now
    else:
        note = MeetingNote(meeting_id=meeting_id, content=content, last_editor_id=user_id, last_edited_at=now)
        db.add(note)
    db.commit()
    db.refresh(note)
    return note


async def create_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> Dict[str, object]:
    get_meeting(db, meeting_id, user_id, raise_404=True)
    existing = _get_note(db, meeting_id)
    if existing:
        raise HTTPException(status_code=409, detail="Meeting note already exists")
    summary = await generate_meeting_summary(db, meeting_id, user_id)
    content: str = summary["content"]  # type: ignore
    summaries = summary["summaries"]  # type: ignore
    sections = summary["sections"]  # type: ignore
    note = upsert_meeting_note(db, meeting_id, user_id, content)
    return {
        "note": note,
        "content": content,
        "summaries": summaries,
        "sections": sections,
    }


async def update_meeting_note(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    *,
    content: Optional[str] = None,
    sections: Optional[Sequence[str]] = None,
) -> MeetingNote:
    note = get_meeting_note(db, meeting_id, user_id)
    materialized = content
    if materialized is None:
        normalized = normalize_summary_sections(sections)
        summary = await generate_meeting_summary(db, meeting_id, user_id, normalized)
        materialized = summary["content"]  # type: ignore
    return upsert_meeting_note(db, meeting_id, user_id, materialized)


def delete_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> None:
    note = get_meeting_note(db, meeting_id, user_id)
    db.delete(note)
    db.commit()
