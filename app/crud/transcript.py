import uuid
from typing import List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.meeting import Meeting, ProjectMeeting, Transcript
from app.models.project import Project, UserProject


def crud_get_transcript(db: Session, transcript_id: Optional[uuid.UUID] = None, meeting_id: Optional[uuid.UUID] = None) -> Optional[Transcript]:
    query = db.query(Transcript).options(joinedload(Transcript.meeting), joinedload(Transcript.audio_concat_file))
    if transcript_id:
        return query.filter(Transcript.id == transcript_id).first()
    if meeting_id:
        return query.filter(Transcript.meeting_id == meeting_id).first()
    return None


def crud_get_transcripts(
    db: Session,
    user_id: uuid.UUID,
    content_search: Optional[str] = None,
    meeting_id: Optional[uuid.UUID] = None,
    page: int = 1,
    limit: int = 20,
) -> Tuple[List[Transcript], int]:
    query = db.query(Transcript).options(joinedload(Transcript.meeting), joinedload(Transcript.audio_concat_file))
    accessible_meetings = db.query(Meeting.id).outerjoin(ProjectMeeting).outerjoin(Project).outerjoin(UserProject).filter(or_(Meeting.is_personal == True and Meeting.created_by == user_id, UserProject.user_id == user_id)).subquery()
    query = query.filter(Transcript.meeting_id.in_(accessible_meetings))
    if content_search:
        query = query.filter(or_(Transcript.content.ilike(f"%{content_search}%"), Transcript.extracted_text_for_search.ilike(f"%{content_search}%")))
    if meeting_id:
        query = query.filter(Transcript.meeting_id == meeting_id)
    total = query.count()
    transcripts = query.offset((page - 1) * limit).limit(limit).all()
    return transcripts, total


def crud_create_transcript(db: Session, **transcript_data) -> Transcript:
    existing = db.query(Transcript).filter(Transcript.meeting_id == transcript_data.get("meeting_id")).first()
    if existing:
        existing.content = transcript_data.get("content")
        existing.audio_concat_file_id = transcript_data.get("audio_concat_file_id")
        db.commit()
        db.refresh(existing)
        return existing
    transcript = Transcript(**transcript_data)
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript


def crud_update_transcript(db: Session, transcript_id: uuid.UUID, **updates) -> Optional[Transcript]:
    transcript = crud_get_transcript(db, transcript_id)
    if not transcript:
        return None
    for key, value in updates.items():
        if hasattr(transcript, key):
            setattr(transcript, key, value)
    db.commit()
    db.refresh(transcript)
    return transcript


def crud_delete_transcript(db: Session, transcript_id: uuid.UUID) -> bool:
    transcript = crud_get_transcript(db, transcript_id)
    if not transcript:
        return False
    db.delete(transcript)
    db.commit()
    return True


def crud_check_transcript_meeting_match(db: Session, transcript_id: uuid.UUID, meeting_id: uuid.UUID) -> bool:
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        return False
    return transcript.meeting_id == meeting_id
