from datetime import datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingNote, Transcript
from app.models.user import User
from app.utils.llm import chat_complete
from app.utils.meeting import check_meeting_access


async def summarize_meeting(meeting_id: UUID, db: Session, current_user: User) -> MeetingNote:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id, Meeting.is_deleted == False).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    if not check_meeting_access(db, meeting, current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
    if not transcript or not transcript.content:
        raise HTTPException(status_code=404, detail="Transcript not found")
    system_prompt = "You are an assistant that summarizes meeting transcripts into structured notes."
    user_prompt = f"Transcript:\n{transcript.content}\n\nCreate sections for Objective, Discussion, Decision, Action Items."
    try:
        summary = await chat_complete(system_prompt, user_prompt)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to generate meeting summary")
    now = datetime.utcnow()
    note = db.query(MeetingNote).filter(MeetingNote.meeting_id == meeting_id).first()
    if note:
        note.content = summary
        note.last_editor_id = current_user.id
        note.last_edited_at = now
    else:
        note = MeetingNote(meeting_id=meeting_id, content=summary, last_editor_id=current_user.id, last_edited_at=now)
        db.add(note)
    db.commit()
    db.refresh(note)
    return note
