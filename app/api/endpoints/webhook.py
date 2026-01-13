import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.constants.messages import MessageConstants
from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.audio_file import AudioFileApiResponse, AudioFileCreate
from app.schemas.webhook import WebhookAudioRequest
from app.services.audio_file import create_audio_file
from app.utils.auth import get_current_user
from app.utils.http import download_file_from_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_V1_STR, tags=["Webhook"])


@router.post("/webhook/audio", response_model=AudioFileApiResponse)
def webhook_audio_upload(
    request: WebhookAudioRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Webhook audio upload request: meeting_id={request.meeting_id}, url={request.file_url}")

    try:
        file_content, content_type = download_file_from_url(str(request.file_url))
        logger.info(f"Downloaded {len(file_content)} bytes, content_type={content_type}")

        audio_data = AudioFileCreate(meeting_id=request.meeting_id, uploaded_by=current_user.id)
        audio_file = create_audio_file(db, audio_data, file_content, content_type)

        if not audio_file:
            logger.error("Failed to create audio file record")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=MessageConstants.OPERATION_FAILED)

        logger.info(f"Successfully created audio file: id={audio_file.id}")
        return {
            "success": True,
            "message": MessageConstants.AUDIO_UPLOADED_SUCCESS,
            "data": audio_file,
        }

    except requests.RequestException as e:
        logger.error(f"Failed to download file from {request.file_url}: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.OPERATION_FAILED)
    except ValueError as e:
        logger.error(f"File validation error: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MessageConstants.VALIDATION_ERROR)
    except Exception as e:
        logger.error(f"Error processing webhook audio upload: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=MessageConstants.INTERNAL_SERVER_ERROR)
