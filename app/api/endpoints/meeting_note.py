from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.meeting_note import MeetingNoteRequest, MeetingNoteSummaryResponse
from app.schemas.user import MeetingNoteResponse
from app.services.meeting_note import (
    create_meeting_note,
    delete_meeting_note,
    get_meeting_note,
    update_meeting_note,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Meeting Notes"])


@router.post("/meetings/{meeting_id}/notes", response_model=ApiResponse[MeetingNoteSummaryResponse])
async def create_meeting_note_endpoint(
    meeting_id: UUID,
    use_ai: bool = Query(True, description="Generate note with the AI meeting agent when available"),
    custom_prompt: Optional[str] = Query(None, description="Optional custom instructions for the AI agent"),
    meeting_type_hint: Optional[str] = Query(None, description="Optional meeting type hint for the AI agent"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await create_meeting_note(
        db,
        meeting_id,
        current_user.id,
        use_ai=use_ai,
        custom_prompt=custom_prompt,
        meeting_type_hint=meeting_type_hint,
    )
    payload = MeetingNoteSummaryResponse(
        note=MeetingNoteResponse.model_validate(result["note"]),
        content=result["content"],
        summaries=result["summaries"],
        sections=result["sections"],
        # ai=result.get("ai"),
    )
    return ApiResponse(success=True, message="Meeting note created", data=payload)


@router.get("/meetings/{meeting_id}/notes", response_model=ApiResponse[MeetingNoteResponse])
def get_meeting_note_endpoint(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = get_meeting_note(db, meeting_id, current_user.id)
    return ApiResponse(success=True, message="Meeting note retrieved", data=MeetingNoteResponse.model_validate(note))


@router.put("/meetings/{meeting_id}/notes", response_model=ApiResponse[MeetingNoteResponse])
async def update_meeting_note_endpoint(
    meeting_id: UUID,
    payload: MeetingNoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = await update_meeting_note(
        db,
        meeting_id,
        current_user.id,
        content=payload.content,
        sections=payload.sections,
    )
    return ApiResponse(success=True, message="Meeting note updated", data=MeetingNoteResponse.model_validate(note))


@router.delete("/meetings/{meeting_id}/notes", response_model=ApiResponse[None])
def delete_meeting_note_endpoint(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_meeting_note(db, meeting_id, current_user.id)
    return ApiResponse(success=True, message="Meeting note deleted")