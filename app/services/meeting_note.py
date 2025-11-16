from datetime import datetime
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
from app.services.transcript import get_transcript_by_meeting
from app.utils.meeting_agent import MeetingAnalyzer


def get_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> Optional[MeetingNote]:
    print(f"\033[94m[get_meeting_note] START - meeting_id: {meeting_id}, user_id: {user_id}\033[0m")
    get_meeting(db, meeting_id, user_id, raise_404=True)
    note = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
    print(f"\033[94m[get_meeting_note] END - note found: {note is not None}\033[0m")
    return note


async def create_meeting_note(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    custom_prompt: Optional[str] = None,
    meeting_type_hint: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    print(f"\033[92m[create_meeting_note] START - meeting_id: {meeting_id}, user_id: {user_id}\033[0m")
    get_meeting(db, meeting_id, user_id, raise_404=True)

    existing = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
    if existing:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting_note.create_failed",
                actor_user_id=user_id,
                target_type="meeting_note",
                target_id=meeting_id,
                metadata={"reason": "already_exists"},
            )
        )
        print("\033[93m[create_meeting_note] ABORT - note already exists\033[0m")
        return None

    transcript = get_transcript_by_meeting(db, meeting_id, user_id)
    if not transcript or not transcript.content:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting_note.create_failed",
                actor_user_id=user_id,
                target_type="meeting_note",
                target_id=meeting_id,
                metadata={"reason": "no_transcript"},
            )
        )
        print("\033[93m[create_meeting_note] ABORT - no transcript found\033[0m")
        return None
    print(f"\033[92m[create_meeting_note] Transcript found, content length: {len(transcript.content)}\033[0m")

    print("\033[92m[create_meeting_note] Generating AI note content...\033[0m")
    ai_result = await generate_meeting_note_content(
        transcript.content,
        meeting_type_hint=meeting_type_hint,
        custom_prompt=custom_prompt,
    )

    if not ai_result.get("content"):
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting_note.create_failed",
                actor_user_id=user_id,
                target_type="meeting_note",
                target_id=meeting_id,
                metadata={"reason": "generation_failed"},
            )
        )
        print("\033[93m[create_meeting_note] ABORT - AI generation failed\033[0m")
        return None
    print(f"\033[92m[create_meeting_note] AI note generated, content length: {len(ai_result['content'])}\033[0m")

    note = MeetingNote(meeting_id=meeting_id, content=ai_result["content"], last_editor_id=user_id, last_edited_at=datetime.utcnow())

    db.add(note)
    db.commit()
    db.refresh(note)
    EventManager.emit_domain_event(
        BaseDomainEvent(
            event_name="meeting_note.created",
            actor_user_id=user_id,
            target_type="meeting_note",
            target_id=meeting_id,
            metadata={"content_length": len(note.content)},
        )
    )
    print(f"\033[92m[create_meeting_note] END - note saved: {note.id}\033[0m")

    # Process and persist task items
    task_items_data = ai_result.get("task_items", [])
    persisted_tasks = []
    if task_items_data:
        print(f"\033[92m[create_meeting_note] Processing {len(task_items_data)} task items for persistence...\033[0m")
        persisted_tasks = process_and_persist_task_items(db, meeting_id, user_id, task_items_data)
        print(f"\033[92m[create_meeting_note] {len(persisted_tasks)} tasks persisted to database\033[0m")

    return {
        "note": note,
        "content": ai_result["content"],
        "task_items": persisted_tasks,
        "decision_items": ai_result.get("decision_items", []),
        "question_items": ai_result.get("question_items", []),
        "token_usage": ai_result.get("token_usage", {}),
    }


async def generate_meeting_note_content(
    transcript_content: str,
    meeting_type_hint: Optional[str] = None,
    custom_prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate meeting note content using AI agent"""
    print(f"\033[96m[generate_meeting_note_content] START - transcript length: {len(transcript_content)}\033[0m")
    try:
        analyzer = MeetingAnalyzer()
        print("\033[96m[generate_meeting_note_content] MeetingAnalyzer created\033[0m")
        result = await analyzer.complete(
            transcript=transcript_content,
            meeting_type=meeting_type_hint,
            custom_prompt=custom_prompt,
        )
        print(f"\033[96m[generate_meeting_note_content] AI analysis complete, result keys: {list(result.keys())}\033[0m")
        print(f"\033[96m[generate_meeting_note_content] content: {result}\033[0m")

        is_informative = bool(result.get("is_informative", True))
        meeting_note = (result.get("meeting_note") or "").strip()

        if is_informative and meeting_note:
            print(f"\033[96m[generate_meeting_note_content] Success - note length: {len(meeting_note)}\033[0m")
            return {
                "content": meeting_note,
                "task_items": result.get("task_items", []),
                "decision_items": result.get("decision_items", []),
                "question_items": result.get("question_items", []),
                "token_usage": result.get("token_usage", {}),
            }
        else:
            print(f"\033[96m[generate_meeting_note_content] Not informative or empty - is_informative: {is_informative}\033[0m")

    except Exception as e:
        print(f"\033[91m[generate_meeting_note_content] ERROR - {str(e)}\033[0m")

    print("\033[96m[generate_meeting_note_content] Returning empty result\033[0m")
    return {
        "content": "",
        "task_items": [],
        "decision_items": [],
        "question_items": [],
        "token_usage": {},
    }


def process_and_persist_task_items(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    task_items: List[Dict[str, Any]],
) -> List[Task]:
    """
    Process AI-extracted task items and persist them to database.

    Converts AI task schema (with string due_dates) to database Task records
    with proper relationships and datetime conversions.

    Args:
        db: Database session
        meeting_id: Meeting to link tasks to
        user_id: User creating the tasks (becomes creator_id)
        task_items: List of task dictionaries from AI extraction

    Returns:
        List of created Task records
    """
    created_tasks: List[Task] = []

    if not task_items:
        print("[process_and_persist_task_items] No task items to persist")
        return created_tasks

    print(f"[process_and_persist_task_items] START - processing {len(task_items)} tasks for meeting {meeting_id}")

    for idx, task_item in enumerate(task_items):
        try:
            # Extract title from description (first 60 chars or first sentence)
            description = task_item.get("description", "").strip()
            title = description[:60] if description else f"Task {idx + 1}"

            # Create TaskCreate schema with parsed values
            task_create = TaskCreate(
                title=title,
                description=description,
                status=task_item.get("status", "todo"),
                priority=task_item.get("priority", "Trung bình"),
                due_date=task_item.get("due_date"),  # Will be parsed in Task.__init__
                meeting_id=meeting_id,
                project_ids=task_item.get("project_ids", []),
            )

            # Create task via service layer (handles permissions and events)
            created_task = create_task(db, task_create, user_id)
            created_tasks.append(created_task)
            print(f"[process_and_persist_task_items] Created task {idx + 1}/{len(task_items)}: {title[:40]}...")

        except Exception as e:
            print(f"[process_and_persist_task_items] ERROR creating task {idx + 1}: {str(e)}")
            # Continue processing remaining tasks even if one fails
            continue

    print(f"[process_and_persist_task_items] END - {len(created_tasks)}/{len(task_items)} tasks persisted")
    return created_tasks


def update_meeting_note(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    content: str,
) -> Optional[MeetingNote]:
    print(f"\033[95m[update_meeting_note] START - meeting_id: {meeting_id}, user_id: {user_id}\033[0m")
    note = get_meeting_note(db, meeting_id, user_id)
    if not note:
        print("\033[95m[update_meeting_note] ABORT - note not found\033[0m")
        return None
    original_content = note.content
    note.content = content
    note.last_editor_id = user_id
    note.last_edited_at = datetime.utcnow()
    db.commit()
    db.refresh(note)
    if original_content != note.content:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting_note.updated",
                actor_user_id=user_id,
                target_type="meeting_note",
                target_id=meeting_id,
                metadata={"diff": {"content": [original_content, note.content]}},
            )
        )
    print(f"\033[95m[update_meeting_note] END - note updated: {note.id}\033[0m")
    return note


def delete_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> bool:
    print(f"\033[91m[delete_meeting_note] START - meeting_id: {meeting_id}, user_id: {user_id}\033[0m")
    note = get_meeting_note(db, meeting_id, user_id)
    if not note:
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting_note.delete_failed",
                actor_user_id=user_id,
                target_type="meeting_note",
                target_id=meeting_id,
                metadata={"reason": "not_found"},
            )
        )
        print("\033[91m[delete_meeting_note] ABORT - note not found\033[0m")
        return False
    db.delete(note)
    db.commit()
    EventManager.emit_domain_event(
        BaseDomainEvent(
            event_name="meeting_note.deleted",
            actor_user_id=user_id,
            target_type="meeting_note",
            target_id=meeting_id,
            metadata={},
        )
    )
    print("\033[91m[delete_meeting_note] END - note deleted\033[0m")
    return True
