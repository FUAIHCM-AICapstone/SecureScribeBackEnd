import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.meeting import AudioFile
from app.schemas.audio_file import AudioFileCreate, AudioFileUpdate
from app.utils.minio import (
    delete_file_from_minio,
    file_exists_in_minio,
    generate_presigned_url,
    upload_bytes_to_minio,
)


def get_file_extension(content_type: str) -> str:
    """Get file extension based on content type"""
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
    audio_file = AudioFile(**audio_data.model_dump())
    db.add(audio_file)
    db.commit()
    db.refresh(audio_file)

    bucket_name = "audio-files"
    file_extension = get_file_extension(content_type)
    object_name = f"{audio_file.id}{file_extension}"

    if upload_bytes_to_minio(file_bytes, bucket_name, object_name, content_type):
        audio_file.file_url = generate_presigned_url(bucket_name, object_name)
        db.commit()
        db.refresh(audio_file)
        return audio_file

    db.delete(audio_file)
    db.commit()
    return None


def get_audio_file(db: Session, audio_id: uuid.UUID) -> Optional[AudioFile]:
    return db.query(AudioFile).filter(AudioFile.id == audio_id).first()


def get_audio_files_by_meeting(db: Session, meeting_id: uuid.UUID) -> List[AudioFile]:
    return db.query(AudioFile).filter(AudioFile.meeting_id == meeting_id).order_by(AudioFile.seq_order, AudioFile.created_at).all()


def update_audio_file(db: Session, audio_id: uuid.UUID, updates: AudioFileUpdate) -> Optional[AudioFile]:
    audio_file = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    if not audio_file:
        return None

    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(audio_file, key, value)

    db.commit()
    db.refresh(audio_file)
    return audio_file


def delete_audio_file(db: Session, audio_id: uuid.UUID) -> bool:
    audio_file = db.query(AudioFile).filter(AudioFile.id == audio_id).first()
    if not audio_file:
        return False

    bucket_name = "audio-files"
    # Try to determine extension from file_url or try common extensions
    object_name = None
    if audio_file.file_url:
        # Extract object name from URL
        try:
            url_parts = audio_file.file_url.split("/")
            if len(url_parts) >= 2:
                object_name = url_parts[-1].split("?")[0]  # Remove query params
        except:
            pass

    # Fallback: try common extensions
    if not object_name:
        for ext in [".webm", ".wav", ".mp3", ".m4a"]:
            test_object = f"{audio_id}{ext}"
            if file_exists_in_minio(bucket_name, test_object):
                object_name = test_object
                break

    if object_name:
        delete_file_from_minio(bucket_name, object_name)

    db.delete(audio_file)
    db.commit()
    return True
