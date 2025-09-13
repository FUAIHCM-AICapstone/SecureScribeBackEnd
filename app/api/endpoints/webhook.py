import uuid
import requests
import logging
from typing import Tuple
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.audio_file import AudioFileApiResponse, AudioFileCreate
from app.services.audio_file import create_audio_file
from app.utils.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.API_V1_STR, tags=["Webhook"])

class WebhookAudioRequest(BaseModel):
    meeting_id: uuid.UUID
    file_url: HttpUrl

def download_file_from_url(url: str) -> Tuple[bytes, str]:
    """Download file from URL and return content with content type"""
    headers = {
        'User-Agent': 'SecureScribe-Bot/1.0',
        'Accept': 'audio/*, video/webm, */*'
    }
    
    response = requests.get(url, timeout=60, stream=True, headers=headers)
    response.raise_for_status()
    
    content_length = response.headers.get('content-length')
    if content_length and int(content_length) > 100 * 1024 * 1024:
        raise ValueError("File too large (>100MB)")
    
    file_content = bytearray()
    for chunk in response.iter_content(chunk_size=8192):
        file_content.extend(chunk)
        if len(file_content) > 100 * 1024 * 1024:
            raise ValueError("File too large (>100MB)")
    
    if len(file_content) == 0:
        raise ValueError("Downloaded file is empty")
    
    content_type = response.headers.get('content-type', 'audio/webm')
    return bytes(file_content), content_type

@router.post("/webhook/audio", response_model=AudioFileApiResponse)
def webhook_audio_upload(request: WebhookAudioRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    logger.info(f"Webhook audio upload request: meeting_id={request.meeting_id}, url={request.file_url}")
    
    try:
        file_content, content_type = download_file_from_url(str(request.file_url))
        logger.info(f"Downloaded {len(file_content)} bytes, content_type={content_type}")
        
        audio_data = AudioFileCreate(meeting_id=request.meeting_id, uploaded_by=current_user.id)
        audio_file = create_audio_file(db, audio_data, file_content, content_type)
        
        if not audio_file:
            logger.error("Failed to create audio file record")
            raise HTTPException(status_code=500, detail="Failed to save audio file")
        
        logger.info(f"Successfully created audio file: id={audio_file.id}")
        return {"success": True, "message": "Audio file uploaded successfully", "data": audio_file}
    
    except requests.RequestException as e:
        logger.error(f"Failed to download file from {request.file_url}: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to download file: {str(e)}")
    except ValueError as e:
        logger.error(f"File validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing webhook audio upload: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
