import uuid
import logging
from typing import List
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.audio_file import (
    AudioFileApiResponse,
    AudioFileCreate,
    AudioFileResponse,
    AudioFileUpdate,
)
from app.schemas.common import ApiResponse
from app.services.audio_file import (
    create_audio_file,
    get_audio_file,
    get_audio_files_by_meeting,
    update_audio_file,
    delete_audio_file,
)
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_V1_STR, tags=["Audio Files"])


@router.post("/audio-files/upload", response_model=AudioFileApiResponse)
def upload_audio_file(
    file: UploadFile = File(...),
    meeting_id: uuid.UUID = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Audio upload attempt: filename={file.filename}, content_type={file.content_type}, size={file.size}")

    # Expanded list of supported audio formats including webm
    supported_formats = [
        "audio/webm",
        "audio/wav",
        "audio/mp3",
        "audio/mpeg",
        "audio/m4a",
        "audio/mp4",
        "video/webm",  # Sometimes webm files are detected as video/webm
    ]

    if file.content_type not in supported_formats:
        error_msg = f"Invalid audio format: {file.content_type}. Supported formats: {', '.join(supported_formats)}"
        logger.error(error_msg)
        raise HTTPException(status_code=400, detail=error_msg)

    try:
        file_content = file.file.read()
        logger.info(f"Read {len(file_content)} bytes from uploaded file")

        if len(file_content) == 0:
            error_msg = "Uploaded file is empty"
            logger.error(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)

        audio_data = AudioFileCreate(meeting_id=meeting_id or uuid.uuid4(), uploaded_by=current_user.id)
        audio_file = create_audio_file(db, audio_data, file_content, file.content_type)

        if not audio_file:
            error_msg = "Failed to upload audio file to storage"
            logger.error(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)

        logger.info(f"Successfully uploaded audio file: {audio_file.id}")
        return ApiResponse(
            success=True,
            message="Audio file uploaded successfully",
            data=AudioFileResponse.model_validate(audio_file),
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Unexpected error during audio upload: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/audio-files/{audio_id}", response_model=AudioFileApiResponse)
def get_audio_file_endpoint(
    audio_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    audio_file = get_audio_file(db, audio_id)
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")

    return ApiResponse(
        success=True,
        message="Audio file retrieved successfully",
        data=AudioFileResponse.model_validate(audio_file),
    )


@router.get("/meetings/{meeting_id}/audio-files")
def get_meeting_audio_files(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    audio_files = get_audio_files_by_meeting(db, meeting_id)
    return ApiResponse(
        success=True,
        message="Audio files retrieved successfully",
        data=[AudioFileResponse.model_validate(af) for af in audio_files],
    )


@router.put("/audio-files/{audio_id}", response_model=AudioFileApiResponse)
def update_audio_file_endpoint(
    audio_id: uuid.UUID,
    updates: AudioFileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    audio_file = update_audio_file(db, audio_id, updates)
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")

    return ApiResponse(
        success=True,
        message="Audio file updated successfully",
        data=AudioFileResponse.model_validate(audio_file),
    )


@router.delete("/audio-files/{audio_id}")
def delete_audio_file_endpoint(
    audio_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not delete_audio_file(db, audio_id):
        raise HTTPException(status_code=404, detail="Audio file not found")

    return ApiResponse(success=True, message="Audio file deleted successfully", data={})
