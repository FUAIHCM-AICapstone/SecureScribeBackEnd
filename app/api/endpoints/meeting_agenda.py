from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.constants.messages import MessageConstants
from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.meeting_agenda import MeetingAgendaGenerateResponse, MeetingAgendaRequest, MeetingAgendaResponse
from app.services.meeting_agenda import delete_meeting_agenda, generate_meeting_agenda_with_ai, get_meeting_agenda, update_meeting_agenda
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Meeting Agenda"])


@router.get("/meetings/{meeting_id}/agenda", response_model=ApiResponse[MeetingAgendaResponse])
def get_meeting_agenda_endpoint(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get meeting agenda for a specific meeting."""
    agenda = get_meeting_agenda(db, meeting_id, current_user.id)
    if agenda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageConstants.MEETING_AGENDA_NOT_FOUND)
    return ApiResponse(
        success=True,
        message=MessageConstants.MEETING_AGENDA_RETRIEVED_SUCCESS,
        data=MeetingAgendaResponse(
            id=str(agenda.id),
            content=agenda.content,
            last_edited_at=agenda.last_edited_at.isoformat() if agenda.last_edited_at else None,
            created_at=agenda.created_at.isoformat(),
            updated_at=agenda.updated_at.isoformat() if agenda.updated_at else None,
        ),
    )


@router.put("/meetings/{meeting_id}/agenda", response_model=ApiResponse[MeetingAgendaResponse])
def update_meeting_agenda_endpoint(
    meeting_id: UUID,
    payload: MeetingAgendaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update meeting agenda content."""
    agenda = update_meeting_agenda(
        db,
        meeting_id,
        current_user.id,
        content=payload.content,
    )
    if agenda is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageConstants.MEETING_AGENDA_NOT_FOUND)
    return ApiResponse(
        success=True,
        message=MessageConstants.MEETING_AGENDA_UPDATED_SUCCESS,
        data=MeetingAgendaResponse(
            id=str(agenda.id),
            content=agenda.content,
            last_edited_at=agenda.last_edited_at.isoformat() if agenda.last_edited_at else None,
            created_at=agenda.created_at.isoformat(),
            updated_at=agenda.updated_at.isoformat() if agenda.updated_at else None,
        ),
    )


@router.post("/meetings/{meeting_id}/agenda/generate", response_model=ApiResponse[MeetingAgendaGenerateResponse])
def generate_meeting_agenda_endpoint(
    meeting_id: UUID,
    custom_prompt: Optional[str] = Query(None, description="Optional custom prompt for AI generation", max_length=1000),
    meeting_type_hint: Optional[str] = Query(None, description="Optional hint for meeting type: business, technical, brainstorming, review, planning, training"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate meeting agenda using AI."""
    # Validate meeting_type_hint if provided
    valid_types = {"business", "technical", "brainstorming", "review", "planning", "training"}
    if meeting_type_hint and meeting_type_hint not in valid_types:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid meeting_type_hint. Must be one of: {', '.join(valid_types)}")

    result = generate_meeting_agenda_with_ai(db, meeting_id, current_user.id, custom_prompt, meeting_type_hint)

    return ApiResponse(
        success=True,
        message=MessageConstants.MEETING_AGENDA_GENERATED_SUCCESS,
        data=result,
    )


@router.delete("/meetings/{meeting_id}/agenda", response_model=ApiResponse[None])
def delete_meeting_agenda_endpoint(
    meeting_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete meeting agenda."""
    success = delete_meeting_agenda(db, meeting_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MessageConstants.MEETING_AGENDA_NOT_FOUND)
    return ApiResponse(success=True, message=MessageConstants.MEETING_AGENDA_DELETED_SUCCESS)
