import os
import tempfile
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.meeting import Transcript
from app.schemas.transcript import TranscriptCreate
from app.services.audio_file import get_audio_file, get_audio_files_by_meeting
from app.utils.inference import transcriber_bytes
from app.utils.minio import download_file_from_minio


def transcribe_meeting(db: Session, meeting_id: uuid.UUID) -> Optional[Transcript]:
    audio_files = get_audio_files_by_meeting(db, meeting_id)
    if not audio_files:
        return None
    
    concat_file = next((af for af in audio_files if af.is_concatenated), audio_files[0])
    return transcribe_audio_file(db, concat_file.id)


def transcribe_audio_file(db: Session, audio_id: uuid.UUID) -> Optional[Transcript]:
    audio_file = get_audio_file(db, audio_id)
    if not audio_file or not audio_file.file_url:
        return None

    bucket_name = "audio-files"
    object_name = f"{audio_file.id}.webm"

    audio_bytes = download_file_from_minio(bucket_name, object_name)
    if not audio_bytes:
        return None

    transcript_text = transcriber_bytes(audio_bytes)
    transcript_data = TranscriptCreate(
        meeting_id=audio_file.meeting_id,
        content=transcript_text,
        audio_concat_file_id=audio_file.id,
    )
    return create_transcript(db, transcript_data)


def create_transcript(db: Session, transcript_data: TranscriptCreate) -> Optional[Transcript]:
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


def get_transcript_by_meeting(db: Session, meeting_id: uuid.UUID) -> Optional[Transcript]:
    return db.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
