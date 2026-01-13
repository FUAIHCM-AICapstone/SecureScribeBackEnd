import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.audio_file import (
    crud_create_audio_file,
    crud_delete_audio_file,
    crud_get_audio_file,
    crud_get_audio_files_by_meeting,
    crud_update_audio_file,
)
from app.models.meeting import AudioFile
from app.schemas.audio_file import AudioFileCreate, AudioFileUpdate


def get_file_extension(content_type: str) -> str:
    extensions = {
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/mp3": ".mp3",
        "audio/mpeg": ".mp3",
        "audio/m4a": ".m4a",
        "audio/mp4": ".m4a",
    }
    return extensions.get(content_type, ".webm")


def create_audio_file(
    db: Session,
    audio_data: AudioFileCreate,
    file_bytes: bytes,
    content_type: str = "audio/webm",
) -> Optional[AudioFile]:
    return crud_create_audio_file(db, audio_data, file_bytes, content_type)


def get_audio_file(db: Session, audio_id: uuid.UUID) -> Optional[AudioFile]:
    return crud_get_audio_file(db, audio_id)


def get_audio_files_by_meeting(db: Session, meeting_id: uuid.UUID) -> List[AudioFile]:
    return crud_get_audio_files_by_meeting(db, meeting_id)


def update_audio_file(db: Session, audio_id: uuid.UUID, updates: AudioFileUpdate) -> Optional[AudioFile]:
    return crud_update_audio_file(db, audio_id, updates)


def delete_audio_file(db: Session, audio_id: uuid.UUID) -> bool:
    return crud_delete_audio_file(db, audio_id)
