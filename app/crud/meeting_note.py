from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.meeting import MeetingNote
from app.models.task import Task


def crud_get_meeting_note(db: Session, meeting_id: UUID) -> Optional[MeetingNote]:
    return db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()


def crud_create_meeting_note(db: Session, meeting_id: UUID, content: str, last_editor_id: UUID) -> MeetingNote:
    note = MeetingNote(meeting_id=meeting_id, content=content, last_editor_id=last_editor_id, last_edited_at=datetime.now(timezone.utc))
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def crud_update_meeting_note(db: Session, meeting_id: UUID, content: str, last_editor_id: UUID) -> Optional[MeetingNote]:
    note = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
    if not note:
        return None
    note.content = content
    note.last_editor_id = last_editor_id
    note.last_edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)
    return note


def crud_delete_meeting_note(db: Session, meeting_id: UUID) -> bool:
    note = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
    if not note:
        return False
    db.delete(note)
    db.commit()
    return True


def crud_delete_meeting_tasks(db: Session, meeting_id: UUID) -> int:
    deleted_count = db.query(Task).filter(Task.meeting_id == meeting_id).delete()
    db.commit()
    return deleted_count
