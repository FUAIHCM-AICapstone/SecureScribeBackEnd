import os
import tempfile
import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.meeting import Meeting, ProjectMeeting, Transcript
from app.models.project import Project
from app.schemas.transcript import TranscriptCreate, TranscriptUpdate
from app.services.audio_file import get_audio_file
from app.utils.inference import transcriber
from app.utils.meeting import check_meeting_access
from app.utils.minio import download_file_from_minio

from .meeting import get_meeting


def check_transcript_access(db: Session, transcript_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        return False
    meeting = get_meeting(db, transcript.meeting_id, user_id)
    if not meeting:
        return False
    return check_meeting_access(db, meeting, user_id)


def transcribe_audio_file(db: Session, audio_id: uuid.UUID) -> Optional[Transcript]:
    audio_file = get_audio_file(db, audio_id)
    if not audio_file or not audio_file.file_url:
        return None
    bucket_name = "audio-files"
    object_name = f"{audio_file.id}.webm"
    audio_bytes = download_file_from_minio(bucket_name, object_name)
    if not audio_bytes:
        return None
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
        temp_file.write(audio_bytes)
        temp_path = temp_file.name
    try:
        transcript_text = transcriber(temp_path)
        transcript_data = TranscriptCreate(meeting_id=audio_file.meeting_id, content=transcript_text, audio_concat_file_id=audio_file.id)
        transcript = create_transcript(db, transcript_data, audio_file.uploaded_by)
        return transcript
    finally:
        os.unlink(temp_path)


def create_transcript(db: Session, transcript_data: TranscriptCreate, user_id: uuid.UUID) -> Transcript:
    meeting = get_meeting(db, transcript_data.meeting_id, user_id)
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    if not check_meeting_access(db, meeting, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to meeting")
    existing = db.query(Transcript).filter(Transcript.meeting_id == transcript_data.meeting_id).first()
    if existing:
        existing.content = transcript_data.content
        existing.audio_concat_file_id = transcript_data.audio_concat_file_id
        db.commit()
        db.refresh(existing)
        return existing
    transcript = Transcript(**transcript_data.model_dump())
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript


def get_transcript(db: Session, transcript_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Transcript]:
    if not check_transcript_access(db, transcript_id, user_id):
        return None
    return db.query(Transcript).options(joinedload(Transcript.meeting), joinedload(Transcript.audio_concat_file)).filter(Transcript.id == transcript_id).first()


def get_transcript_by_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Transcript]:
    meeting = get_meeting(db, meeting_id, user_id)
    if not meeting:
        return None
    if not check_meeting_access(db, meeting, user_id):
        return None
    return db.query(Transcript).options(joinedload(Transcript.meeting), joinedload(Transcript.audio_concat_file)).filter(Transcript.meeting_id == meeting_id).first()


def get_transcripts(db: Session, user_id: uuid.UUID, content_search: Optional[str] = None, meeting_id: Optional[uuid.UUID] = None, page: int = 1, limit: int = 20) -> Tuple[List[Transcript], int]:
    query = db.query(Transcript).options(joinedload(Transcript.meeting), joinedload(Transcript.audio_concat_file))
    accessible_meetings = db.query(Meeting.id).outerjoin(ProjectMeeting).outerjoin(Project).outerjoin(Project.users).filter(or_(Meeting.created_by == user_id, Meeting.is_personal == True, Project.users.any(id=user_id))).subquery()
    query = query.filter(Transcript.meeting_id.in_(accessible_meetings))
    if content_search:
        query = query.filter(or_(Transcript.content.ilike(f"%{content_search}%"), Transcript.extracted_text_for_search.ilike(f"%{content_search}%")))
    if meeting_id:
        query = query.filter(Transcript.meeting_id == meeting_id)
    total = query.count()
    offset = (page - 1) * limit
    transcripts = query.offset(offset).limit(limit).all()
    return transcripts, total


def update_transcript(db: Session, transcript_id: uuid.UUID, transcript_data: TranscriptUpdate, user_id: uuid.UUID) -> Transcript:
    if not check_transcript_access(db, transcript_id, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to transcript")
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")
    updates = transcript_data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        if hasattr(transcript, key):
            setattr(transcript, key, value)
    db.commit()
    db.refresh(transcript)
    return transcript


def delete_transcript(db: Session, transcript_id: uuid.UUID, user_id: uuid.UUID) -> None:
    if not check_transcript_access(db, transcript_id, user_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to transcript")
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found")
    db.delete(transcript)
    db.commit()


def bulk_create_transcripts(db: Session, transcripts_data: List[TranscriptCreate], user_id: uuid.UUID) -> List[dict]:
    results = []
    for transcript_data in transcripts_data:
        try:
            transcript = create_transcript(db, transcript_data, user_id)
            results.append({"success": True, "transcript_id": str(transcript.id), "meeting_id": str(transcript.meeting_id)})
        except Exception as e:
            results.append({"success": False, "meeting_id": str(transcript_data.meeting_id), "error": str(e)})
    return results


def bulk_update_transcripts(db: Session, updates: List[dict], user_id: uuid.UUID) -> List[dict]:
    results = []
    for update_item in updates:
        try:
            transcript = update_transcript(db, update_item["id"], update_item["updates"], user_id)
            results.append({"success": True, "transcript_id": str(transcript.id)})
        except Exception as e:
            results.append({"success": False, "transcript_id": str(update_item["id"]), "error": str(e)})
    return results


def bulk_delete_transcripts(db: Session, transcript_ids: List[uuid.UUID], user_id: uuid.UUID) -> List[dict]:
    results = []
    for transcript_id in transcript_ids:
        try:
            delete_transcript(db, transcript_id, user_id)
            results.append({"success": True, "transcript_id": str(transcript_id)})
        except Exception as e:
            results.append({"success": False, "transcript_id": str(transcript_id), "error": str(e)})
    return results


def serialize_transcript(transcript: Transcript) -> dict:
    return {"id": transcript.id, "meeting_id": transcript.meeting_id, "content": transcript.content, "audio_concat_file_id": transcript.audio_concat_file_id, "extracted_text_for_search": transcript.extracted_text_for_search, "qdrant_vector_id": transcript.qdrant_vector_id, "created_at": transcript.created_at, "updated_at": transcript.updated_at}
