from uuid import UUID

from fastapi import APIRouter, Depends
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
    summarize_meeting_sections_for_chat,
    update_meeting_note,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Meeting Notes"])


@router.post("/meetings/{meeting_id}/notes", response_model=ApiResponse[MeetingNoteSummaryResponse])
def create_meeting_note_endpoint(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = create_meeting_note(db, meeting_id, current_user.id)
    summary = summarize_meeting_sections_for_chat(db, meeting_id, current_user.id)
    payload = MeetingNoteSummaryResponse(
        note=MeetingNoteResponse.model_validate(note),
        content=summary["content"],
        summaries=summary["summaries"],
        sections=summary["sections"],
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
def update_meeting_note_endpoint(
    meeting_id: UUID,
    payload: MeetingNoteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = update_meeting_note(
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
