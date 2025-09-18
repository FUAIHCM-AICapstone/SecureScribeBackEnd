import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.transcript import TranscriptApiResponse, TranscriptResponse
from app.schemas.common import ApiResponse
from app.services.transcript import transcribe_audio_file, transcribe_meeting, get_transcript_by_meeting
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_V1_STR, tags=["Transcripts"])


@router.post("/transcripts/transcribe/{meeting_id}", response_model=TranscriptApiResponse)
def transcribe_meeting_endpoint(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Transcription request for meeting_id: {meeting_id}")

    transcript = transcribe_meeting(db, meeting_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Meeting not found or no audio files available")

    logger.info(f"Transcription completed: {transcript.id}")
    return ApiResponse(
        success=True,
        message="Meeting transcribed successfully",
        data=TranscriptResponse.model_validate(transcript),
    )


@router.post("/transcripts/transcribe-audio/{audio_id}", response_model=TranscriptApiResponse)
def transcribe_audio_endpoint(
    audio_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Transcription request for audio_id: {audio_id}")

    transcript = transcribe_audio_file(db, audio_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Audio file not found or transcription failed")

    logger.info(f"Transcription completed: {transcript.id}")
    return ApiResponse(
        success=True,
        message="Audio transcribed successfully",
        data=TranscriptResponse.model_validate(transcript),
    )


@router.get("/transcripts/meeting/{meeting_id}", response_model=TranscriptApiResponse)
def get_meeting_transcript(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transcript = get_transcript_by_meeting(db, meeting_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    return ApiResponse(
        success=True,
        message="Transcript retrieved successfully",
        data=TranscriptResponse.model_validate(transcript),
    )
