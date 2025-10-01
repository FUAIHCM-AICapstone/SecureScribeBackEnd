from typing import Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.user import MeetingNoteResponse
from app.services.meeting_summary import summarize_meeting
from app.utils.auth import get_current_user


class MeetingSummaryRequest(BaseModel):
    sections: Optional[List[str]] = None


class MeetingSummaryPayload(BaseModel):
    content: str
    sections: Dict[str, str]
    note: Optional[MeetingNoteResponse] = None


router = APIRouter(prefix=settings.API_V1_STR, tags=["Meeting Summary"])


@router.post("/meetings/{meeting_id}/summarize", response_model=ApiResponse[MeetingSummaryPayload])
async def summarize_meeting_endpoint(
    meeting_id: UUID,
    summary_request: MeetingSummaryRequest = Body(default=MeetingSummaryRequest()),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await summarize_meeting(meeting_id, db, current_user, summary_request.sections)
    note = result.get("note")
    payload = MeetingSummaryPayload(
        content=result["content"],
        sections=result["summaries"],
        note=MeetingNoteResponse.model_validate(note) if note else None,
    )
    return ApiResponse(success=True, message="Meeting summarized", data=payload)
