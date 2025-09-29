from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.user import MeetingNoteResponse
from app.services.meeting_summary import summarize_meeting
from app.utils.auth import get_current_user


router = APIRouter(prefix=settings.API_V1_STR, tags=["Meeting Summary"])


@router.post("/meetings/{meeting_id}/summarize", response_model=ApiResponse[MeetingNoteResponse])
async def summarize_meeting_endpoint(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await summarize_meeting(meeting_id, db, current_user)
    return ApiResponse(success=True, message="Meeting summarized", data=MeetingNoteResponse.model_validate(note))
