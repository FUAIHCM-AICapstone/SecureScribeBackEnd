from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
    custom_prompt: Optional[str] = Query(None, description="Optional custom instructions for the AI agent"),
    meeting_type_hint: Optional[str] = Query(None, description="Optional meeting type hint for the AI agent"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = create_meeting_note(
        db,
        meeting_id,
        current_user.id,
        custom_prompt=custom_prompt,
        meeting_type_hint=meeting_type_hint,
    )
    if result is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to create meeting note")

    payload = MeetingNoteSummaryResponse(
        note=MeetingNoteResponse.model_validate(result["note"]),
        content=result["content"],
        task_items=result["task_items"],
        decision_items=result["decision_items"],
        question_items=result["question_items"],
        token_usage=result["token_usage"],
    )
    return ApiResponse(success=True, message="Meeting note created", data=payload)


@router.get("/meetings/{meeting_id}/notes", response_model=ApiResponse[MeetingNoteResponse])
def get_meeting_note_endpoint(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = get_meeting_note(db, meeting_id, current_user.id)
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting note not found")
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
    )
    if note is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting note not found")
    return ApiResponse(success=True, message="Meeting note updated", data=MeetingNoteResponse.model_validate(note))


@router.delete("/meetings/{meeting_id}/notes", response_model=ApiResponse[None])
def delete_meeting_note_endpoint(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    success = delete_meeting_note(db, meeting_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting note not found")
    return ApiResponse(success=True, message="Meeting note deleted")
