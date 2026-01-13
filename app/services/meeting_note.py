from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.events.domain_events import BaseDomainEvent
from app.models.meeting import MeetingNote
from app.models.task import Task
from app.schemas.task import TaskCreate
from app.services.event_manager import EventManager
from app.services.meeting import get_meeting
from app.services.task import create_task


def get_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> Optional[MeetingNote]:
    get_meeting(db, meeting_id, user_id, raise_404=True)
    return db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()


def process_and_persist_task_items(db: Session, meeting_id: UUID, user_id: UUID, task_items: List[Dict[str, Any]]) -> List[Task]:
    created_tasks = []
    for idx, task_item in enumerate(task_items):
        item_dict = task_item.model_dump() if hasattr(task_item, "model_dump") else task_item
        if not isinstance(item_dict, dict):
            continue
        description = item_dict.get("description", "").strip()
        task_create = TaskCreate(title=description or f"Task {idx + 1}", description=description, status=item_dict.get("status", "todo"), priority=item_dict.get("priority", "Trung bình"), due_date=item_dict.get("due_date"), meeting_id=meeting_id, project_ids=item_dict.get("project_ids", []))
        created_tasks.append(create_task(db, task_create, user_id))
    return created_tasks


def update_meeting_note(db: Session, meeting_id: UUID, user_id: UUID, content: str) -> Optional[MeetingNote]:
    note = get_meeting_note(db, meeting_id, user_id)
    if not note:
        return None
    original_content = note.content
    note.content = content
    note.last_editor_id = user_id
    note.last_edited_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)
    if original_content != note.content:
        EventManager.emit_domain_event(BaseDomainEvent(event_name="meeting_note.updated", actor_user_id=user_id, target_type="meeting_note", target_id=meeting_id, metadata={"diff": {"content": [original_content, note.content]}}))
    return note


def delete_meeting_tasks(db: Session, meeting_id: UUID) -> int:
    deleted_count = db.query(Task).filter(Task.meeting_id == meeting_id).delete()
    db.commit()
    return deleted_count


def delete_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> bool:
    note = get_meeting_note(db, meeting_id, user_id)
    if not note:
        return False
    db.delete(note)
    db.commit()
    EventManager.emit_domain_event(BaseDomainEvent(event_name="meeting_note.deleted", actor_user_id=user_id, target_type="meeting_note", target_id=meeting_id, metadata={}))
    return True


def save_meeting_analysis_results(db: Session, meeting_id: UUID, user_id: UUID, meeting_note_content: str, task_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    existing_note = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
    is_regeneration = existing_note is not None
    if is_regeneration:
        delete_meeting_tasks(db, meeting_id)
        existing_note.content = meeting_note_content
        existing_note.last_editor_id = user_id
        existing_note.last_edited_at = datetime.now(timezone.utc)
        note = existing_note
        db.commit()
        db.refresh(note)
        EventManager.emit_domain_event(BaseDomainEvent(event_name="meeting_note.regenerated", actor_user_id=user_id, target_type="meeting_note", target_id=meeting_id, metadata={"content_length": len(note.content), "regenerated": True}))
    else:
        note = MeetingNote(meeting_id=meeting_id, content=meeting_note_content, last_editor_id=user_id, last_edited_at=datetime.now(timezone.utc))
        db.add(note)
        db.commit()
        db.refresh(note)
        EventManager.emit_domain_event(BaseDomainEvent(event_name="meeting_note.created", actor_user_id=user_id, target_type="meeting_note", target_id=meeting_id, metadata={"content_length": len(note.content)}))
    persisted_tasks = process_and_persist_task_items(db, meeting_id, user_id, task_items) if task_items else []
    return {"note": note, "content": meeting_note_content, "task_items": persisted_tasks}
