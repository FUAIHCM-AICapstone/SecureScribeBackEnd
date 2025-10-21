from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.meeting import MeetingNote
from app.services.meeting import get_meeting
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
        print("\033[93m[create_meeting_note] ABORT - note already exists\033[0m")
        return None

    transcript = get_transcript_by_meeting(db, meeting_id, user_id)
    if not transcript or not transcript.content:
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
        print("\033[93m[create_meeting_note] ABORT - AI generation failed\033[0m")
        return None
    print(f"\033[92m[create_meeting_note] AI note generated, content length: {len(ai_result['content'])}\033[0m")

    note = MeetingNote(meeting_id=meeting_id, content=ai_result["content"], last_editor_id=user_id, last_edited_at=datetime.utcnow())

    db.add(note)
    db.commit()
    db.refresh(note)
    print(f"\033[92m[create_meeting_note] END - note saved: {note.id}\033[0m")

    return {
        "note": note,
        "content": ai_result["content"],
        "task_items": ai_result.get("task_items", []),
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
    note.content = content
    note.last_editor_id = user_id
    note.last_edited_at = datetime.utcnow()
    db.commit()
    db.refresh(note)
    print(f"\033[95m[update_meeting_note] END - note updated: {note.id}\033[0m")
    return note


def delete_meeting_note(db: Session, meeting_id: UUID, user_id: UUID) -> bool:
    print(f"\033[91m[delete_meeting_note] START - meeting_id: {meeting_id}, user_id: {user_id}\033[0m")
    note = get_meeting_note(db, meeting_id, user_id)
    if not note:
        print("\033[91m[delete_meeting_note] ABORT - note not found\033[0m")
        return False
    db.delete(note)
    db.commit()
    print("\033[91m[delete_meeting_note] END - note deleted\033[0m")
    return True
