from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.meeting_note import MeetingNoteRequest
from app.schemas.user import MeetingNoteResponse
from app.services.meeting_note import (
    delete_meeting_note,
    get_meeting_note,
    update_meeting_note,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Meeting Notes"])


@router.post("/meetings/{meeting_id}/notes", response_model=ApiResponse[dict])
async def create_meeting_note_endpoint(
    meeting_id: UUID,
    custom_prompt: Optional[str] = Query(None, description="Optional custom instructions for the AI agent"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Queue meeting note generation as a background task.

    Returns task_id immediately. Client should:
    1. Listen to WebSocket for progress updates
    2. Poll GET /meetings/{meeting_id}/notes to get the result when complete

    Progress updates via WebSocket:
    - 0%: Started
    - 10%: Validating transcript
    - 30%: Processing (concurrent extraction)
    - 90%: Saving to database
    - 100%: Completed
    """
    from app.jobs.tasks import process_meeting_analysis_task
    from app.services.meeting import get_meeting
    from app.services.transcript import get_transcript_by_meeting

    # Validate meeting exists and user has access
    get_meeting(db, meeting_id, current_user.id, raise_404=True)

    # Validate transcript exists
    transcript = get_transcript_by_meeting(db, meeting_id, current_user.id)
    if not transcript or not transcript.content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No transcript found for this meeting. Please transcribe the audio first.")

    # Queue the Celery task
    task = process_meeting_analysis_task.delay(
        transcript=transcript.content,
        meeting_id=str(meeting_id),
        user_id=str(current_user.id),
        custom_prompt=custom_prompt,
    )

    return ApiResponse(success=True, message="Meeting note generation queued. Listen to WebSocket for progress updates.", data={"task_id": task.id, "meeting_id": str(meeting_id), "status": "queued", "message": "Task queued successfully. You will receive progress updates via WebSocket."})


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


# @router.get("/meetings/tasks/{task_id}/status", response_model=ApiResponse[dict])
# def get_task_status_endpoint(
#     task_id: str,
#     current_user: User = Depends(get_current_user),
# ):
#     """
#     Get the status of a meeting analysis task.

#     Useful for polling if WebSocket is not available.
#     """
#     from app.jobs.celery_worker import celery_app

#     task = celery_app.AsyncResult(task_id)

#     response_data = {
#         "task_id": task_id,
#         "status": task.state,
#         "ready": task.ready(),
#     }

#     if task.ready():
#         if task.successful():
#             response_data["result"] = task.result
#         elif task.failed():
#             response_data["error"] = str(task.info)

#     return ApiResponse(success=True, message=f"Task status: {task.state}", data=response_data)
