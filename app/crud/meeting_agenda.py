from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.meeting import MeetingAgenda


def crud_get_meeting_agenda(db: Session, meeting_id: UUID) -> Optional[MeetingAgenda]:
    return db.query(MeetingAgenda).filter(MeetingAgenda.meeting_id == meeting_id).first()


def crud_create_meeting_agenda(db: Session, meeting_id: UUID, content: str, last_editor_id: UUID) -> MeetingAgenda:
    agenda = MeetingAgenda(meeting_id=meeting_id, content=content, last_editor_id=last_editor_id, last_edited_at=datetime.now(timezone.utc))
    db.add(agenda)
    db.commit()
    db.refresh(agenda)
    return agenda


def crud_update_meeting_agenda(db: Session, meeting_id: UUID, content: str, last_editor_id: UUID) -> Optional[MeetingAgenda]:
    agenda = db.query(MeetingAgenda).filter(MeetingAgenda.meeting_id == meeting_id).first()
    if not agenda:
        return None
    agenda.content = content
    agenda.last_editor_id = last_editor_id
    agenda.last_edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(agenda)
    return agenda


def crud_delete_meeting_agenda(db: Session, meeting_id: UUID) -> bool:
    agenda = db.query(MeetingAgenda).filter(MeetingAgenda.meeting_id == meeting_id).first()
    if not agenda:
        return False
    db.delete(agenda)
    db.commit()
    return True
