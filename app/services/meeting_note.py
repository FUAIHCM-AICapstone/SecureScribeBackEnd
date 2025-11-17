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
    get_meeting(db, meeting_id, user_id, raise_404=True)
    note = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
    return note


# async def create_meeting_note(
#     db: Session,
#     meeting_id: UUID,
#     user_id: UUID,
#     custom_prompt: Optional[str] = None,
# ) -> Optional[Dict[str, Any]]:
#     """
#     DEPRECATED: Use process_meeting_analysis_task from app.jobs.tasks instead.
    
#     This function is kept for backward compatibility but will be removed in future versions.
#     For new code, queue the Celery task instead:
    
#     from app.jobs.tasks import process_meeting_analysis_task
#     task = process_meeting_analysis_task.delay(transcript, meeting_id, user_id, custom_prompt)
#     """
#     get_meeting(db, meeting_id, user_id, raise_404=True)

#     existing_note = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
#     is_regeneration = existing_note is not None

#     if is_regeneration:
#         delete_meeting_tasks(db, meeting_id)

#     transcript = get_transcript_by_meeting(db, meeting_id, user_id)
#     if not transcript or not transcript.content:
#         EventManager.emit_domain_event(
#             BaseDomainEvent(
#                 event_name="meeting_note.create_failed",
#                 actor_user_id=user_id,
#                 target_type="meeting_note",
#                 target_id=meeting_id,
#                 metadata={"reason": "no_transcript"},
#             )
#         )
#         return None
#     ai_result = await generate_meeting_note_content(
#         transcript.content,
#         custom_prompt=custom_prompt,
#     )

#     if not ai_result.get("content"):
#         EventManager.emit_domain_event(
#             BaseDomainEvent(
#                 event_name="meeting_note.create_failed",
#                 actor_user_id=user_id,
#                 target_type="meeting_note",
#                 target_id=meeting_id,
#                 metadata={"reason": "generation_failed"},
#             )
#         )
#         return None

#     if is_regeneration:
#         # Update existing note
#         existing_note.content = ai_result["content"]
#         existing_note.last_editor_id = user_id
#         existing_note.last_edited_at = datetime.utcnow()
#         note = existing_note
#         db.commit()
#         db.refresh(note)
#         EventManager.emit_domain_event(
#             BaseDomainEvent(
#                 event_name="meeting_note.regenerated",
#                 actor_user_id=user_id,
#                 target_type="meeting_note",
#                 target_id=meeting_id,
#                 metadata={"content_length": len(note.content), "regenerated": True},
#             )
#         )
#     else:
#         # Create new note
#         note = MeetingNote(
#             meeting_id=meeting_id,
#             content=ai_result["content"],
#             last_editor_id=user_id,
#             last_edited_at=datetime.utcnow(),
#         )
#         db.add(note)
#         db.commit()
#         db.refresh(note)
#         EventManager.emit_domain_event(
#             BaseDomainEvent(
#                 event_name="meeting_note.created",
#                 actor_user_id=user_id,
#                 target_type="meeting_note",
#                 target_id=meeting_id,
#                 metadata={"content_length": len(note.content)},
#             )
#         )

#     # Process and persist task items
#     task_items_data = ai_result.get("task_items", [])
#     persisted_tasks = []
#     if task_items_data:
#         persisted_tasks = process_and_persist_task_items(db, meeting_id, user_id, task_items_data)

#     return {
#         "note": note,
#         "content": ai_result["content"],
#         "task_items": persisted_tasks,
#         "decision_items": ai_result.get("decision_items", []),
#         "question_items": ai_result.get("question_items", []),
#         "token_usage": ai_result.get("token_usage", {}),
#     }


# async def generate_meeting_note_content(
#     transcript_content: str,
#     custom_prompt: Optional[str] = None,
# ) -> Dict[str, Any]:
#     """Generate meeting note content using AI agent"""
#     try:
#         analyzer = MeetingAnalyzer()
#         result = await analyzer.complete(
#             transcript=transcript_content,
#             custom_prompt=custom_prompt,
#         )

#         is_informative = bool(result.get("is_informative", True))
#         meeting_note = (result.get("meeting_note") or "").strip()

#         if is_informative and meeting_note:
#             return {
#                 "content": meeting_note,
#                 "task_items": result.get("task_items", []),
#                 "token_usage": result.get("token_usage", {}),
#             }

#     except Exception as e:
#         print(f"[generate_meeting_note_content] Error: {e}")

#     return {
#         "content": "",
#         "task_items": [],
#         "decision_items": [],
#         "question_items": [],
#         "token_usage": {},
#     }


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
        return created_tasks

    for idx, task_item in enumerate(task_items):
        try:
            # Ensure task_item is a dictionary
            if hasattr(task_item, "model_dump"):
                task_item = task_item.model_dump()
            elif not isinstance(task_item, dict):
                continue

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

        except Exception as e:
            print(f"[process_and_persist_task_items] Error creating task {idx + 1}: {str(e)}")
            # Continue processing remaining tasks even if one fails
            continue

    return created_tasks


def update_meeting_note(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    content: str,
) -> Optional[MeetingNote]:
    note = get_meeting_note(db, meeting_id, user_id)
    if not note:
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
    return note


def delete_meeting_tasks(db: Session, meeting_id: UUID) -> int:
    """
    Delete all tasks associated with a meeting.
    Used during note regeneration to clean up old tasks.

    Args:
        db: Database session
        meeting_id: Meeting ID to delete tasks for

    Returns:
        Number of tasks deleted
    """
    deleted_count = db.query(Task).filter(Task.meeting_id == meeting_id).delete()
    db.commit()
    return deleted_count


def delete_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> bool:
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
    return True


def save_meeting_analysis_results(
    db: Session,
    meeting_id: UUID,
    user_id: UUID,
    meeting_note_content: str,
    task_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Save meeting analysis results to database.
    
    This function is called by the Celery task after analysis is complete.
    It handles both new note creation and regeneration.
    
    Args:
        db: Database session
        meeting_id: Meeting UUID
        user_id: User UUID who triggered the analysis
        meeting_note_content: Generated meeting note content
        task_items: List of extracted task items
        
    Returns:
        Dictionary with saved note and tasks
    """
    existing_note = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
    is_regeneration = existing_note is not None

    if is_regeneration:
        # Delete old tasks before regeneration
        delete_meeting_tasks(db, meeting_id)
        
        # Update existing note
        existing_note.content = meeting_note_content
        existing_note.last_editor_id = user_id
        existing_note.last_edited_at = datetime.utcnow()
        note = existing_note
        db.commit()
        db.refresh(note)
        
        EventManager.emit_domain_event(
            BaseDomainEvent(
                event_name="meeting_note.regenerated",
                actor_user_id=user_id,
                target_type="meeting_note",
                target_id=meeting_id,
                metadata={"content_length": len(note.content), "regenerated": True},
            )
        )
    else:
        # Create new note
        note = MeetingNote(
            meeting_id=meeting_id,
            content=meeting_note_content,
            last_editor_id=user_id,
            last_edited_at=datetime.utcnow(),
        )
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

    # Process and persist task items
    persisted_tasks = []
    if task_items:
        persisted_tasks = process_and_persist_task_items(db, meeting_id, user_id, task_items)

    return {
        "note": note,
        "content": meeting_note_content,
        "task_items": persisted_tasks,
    }
