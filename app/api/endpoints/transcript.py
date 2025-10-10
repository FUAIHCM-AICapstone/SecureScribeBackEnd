import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.meeting import Transcript
from app.models.user import User
from app.schemas.common import ApiResponse, create_pagination_meta
from app.schemas.transcript import (
    BulkTranscriptCreate,
    BulkTranscriptDelete,
    BulkTranscriptResponse,
    BulkTranscriptUpdate,
    TranscriptApiResponse,
    TranscriptCreate,
    TranscriptResponse,
    TranscriptsPaginatedResponse,
    TranscriptUpdate,
)
from app.services.transcript import (
    bulk_create_transcripts,
    bulk_delete_transcripts,
    bulk_update_transcripts,
    create_transcript,
    delete_transcript,
    get_transcript,
    get_transcript_by_meeting,
    get_transcripts,
    serialize_transcript,
    transcribe_audio_file,
    update_transcript,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Transcripts"])


@router.post("/transcripts/transcribe/{audio_id}", response_model=TranscriptApiResponse)
def transcribe_audio_endpoint(audio_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    transcript = transcribe_audio_file(db, audio_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Audio file not found or transcription failed")
    return ApiResponse(success=True, message="Audio transcribed successfully", data=TranscriptResponse.model_validate(transcript))


@router.get("/transcripts", response_model=TranscriptsPaginatedResponse)
def get_transcripts_endpoint(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100), content_search: Optional[str] = Query(None), meeting_id: Optional[uuid.UUID] = Query(None)):
    transcripts, total = get_transcripts(db=db, user_id=current_user.id, content_search=content_search, meeting_id=meeting_id, page=page, limit=limit)
    pagination_meta = create_pagination_meta(page, limit, total)
    return TranscriptsPaginatedResponse(success=True, message="Transcripts retrieved successfully", data=[TranscriptResponse.model_validate(t) for t in transcripts], pagination=pagination_meta)


@router.get("/transcripts/{transcript_id}", response_model=TranscriptApiResponse)
def get_transcript_endpoint(transcript_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    transcript = get_transcript(db, transcript_id, current_user.id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return ApiResponse(success=True, message="Transcript retrieved successfully", data=TranscriptResponse.model_validate(transcript))


@router.get("/transcripts/meeting/{meeting_id}", response_model=TranscriptApiResponse)
def get_meeting_transcript_endpoint(meeting_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    transcript = get_transcript_by_meeting(db, meeting_id, current_user.id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return ApiResponse(success=True, message="Transcript retrieved successfully", data=TranscriptResponse.model_validate(transcript))


@router.post("/transcripts", response_model=TranscriptApiResponse)
def create_transcript_endpoint(transcript: TranscriptCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    created_transcript = create_transcript(db, transcript, current_user.id)
    loaded_transcript = get_transcript(db, created_transcript.id, current_user.id)
    return ApiResponse(success=True, message="Transcript created successfully", data=TranscriptResponse.model_validate(loaded_transcript or created_transcript))


@router.put("/transcripts/{transcript_id}", response_model=TranscriptApiResponse)
def update_transcript_endpoint(transcript_id: uuid.UUID, transcript_update: TranscriptUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    updated_transcript = update_transcript(db, transcript_id, transcript_update, current_user.id)
    loaded_transcript = get_transcript(db, transcript_id, current_user.id)
    return ApiResponse(success=True, message="Transcript updated successfully", data=TranscriptResponse.model_validate(loaded_transcript or updated_transcript))


@router.delete("/transcripts/{transcript_id}", response_model=ApiResponse[dict])
def delete_transcript_endpoint(transcript_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    delete_transcript(db, transcript_id, current_user.id)
    return ApiResponse(success=True, message="Transcript deleted successfully", data={"transcript_id": str(transcript_id)})


@router.post("/transcripts/bulk", response_model=BulkTranscriptResponse)
def bulk_create_transcripts_endpoint(bulk_request: BulkTranscriptCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    results = bulk_create_transcripts(db, bulk_request.transcripts, current_user.id)
    total_processed = len(results)
    total_success = sum(1 for r in results if r["success"])
    total_failed = total_processed - total_success
    return BulkTranscriptResponse(success=total_failed == 0, message=f"Bulk transcript creation completed. {total_success} successful, {total_failed} failed.", data=results, total_processed=total_processed, total_success=total_success, total_failed=total_failed)


@router.put("/transcripts/bulk", response_model=BulkTranscriptResponse)
def bulk_update_transcripts_endpoint(bulk_request: BulkTranscriptUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    updates = [{"id": item.id, "updates": item.updates} for item in bulk_request.transcripts]
    results = bulk_update_transcripts(db, updates, current_user.id)
    total_processed = len(results)
    total_success = sum(1 for r in results if r["success"])
    total_failed = total_processed - total_success
    return BulkTranscriptResponse(success=total_failed == 0, message=f"Bulk transcript update completed. {total_success} successful, {total_failed} failed.", data=results, total_processed=total_processed, total_success=total_success, total_failed=total_failed)


@router.delete("/transcripts/bulk", response_model=BulkTranscriptResponse)
def bulk_delete_transcripts_endpoint(bulk_request: BulkTranscriptDelete, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    results = bulk_delete_transcripts(db, bulk_request.transcript_ids, current_user.id)
    total_processed = len(results)
    total_success = sum(1 for r in results if r["success"])
    total_failed = total_processed - total_success
    return BulkTranscriptResponse(success=total_failed == 0, message=f"Bulk transcript deletion completed. {total_success} successful, {total_failed} failed.", data=results, total_processed=total_processed, total_success=total_success, total_failed=total_failed)


@router.post("/transcripts/{transcript_id}/reindex", response_model=ApiResponse[dict])
def reindex_transcript_endpoint(
    transcript_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually trigger re-indexing of a transcript.
    Useful for fixing failed indexing or updating after metadata changes.
    """
    from app.services.transcript import check_transcript_access
    from app.jobs.tasks import index_transcript_task
    
    # Check access
    if not check_transcript_access(db, transcript_id, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this transcript"
        )
    
    # Check transcript exists
    transcript = db.query(Transcript).filter(Transcript.id == transcript_id).first()
    if not transcript:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transcript not found"
        )
    
    # Queue re-indexing task
    try:
        task = index_transcript_task.delay(str(transcript_id))
        return ApiResponse(
            success=True,
            message="Transcript re-indexing queued successfully",
            data={
                "transcript_id": str(transcript_id),
                "task_id": task.id if task else None,
            },
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue re-indexing: {str(e)}"
        )


@router.post("/transcripts/reindex-all", response_model=ApiResponse[dict])
def reindex_all_transcripts_endpoint(
    meeting_id: Optional[uuid.UUID] = Query(None, description="Reindex only transcripts for this meeting"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk re-index transcripts. Admin/maintenance endpoint.
    Can optionally filter by meeting_id.
    """
    from app.models.meeting import Meeting
    from app.jobs.tasks import index_transcript_task
    from app.services.meeting import get_meeting
    from app.utils.meeting import check_meeting_access
    
    # Build query
    query = db.query(Transcript)
    
    if meeting_id:
        # Check access to specific meeting
        meeting = get_meeting(db, meeting_id, current_user.id)
        if not meeting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meeting not found or access denied"
            )
        query = query.filter(Transcript.meeting_id == meeting_id)
    else:
        # For bulk re-index, require user to have access to meetings
        # This is a simplified check - you might want stricter admin-only access
        
        # Get all transcripts user has access to
        accessible_meeting_ids = []
        meetings = db.query(Meeting).filter(Meeting.is_deleted == False).all()
        for meeting in meetings:
            if check_meeting_access(db, meeting, current_user.id):
                accessible_meeting_ids.append(meeting.id)
        
        query = query.filter(Transcript.meeting_id.in_(accessible_meeting_ids))
    
    transcripts = query.all()
    
    # Queue indexing tasks
    queued = 0
    failed = 0
    for transcript in transcripts:
        try:
            index_transcript_task.delay(str(transcript.id))
            queued += 1
        except Exception as e:
            print(f"🔴 Failed to queue transcript {transcript.id}: {e}")
            failed += 1
    
    return ApiResponse(
        success=True,
        message=f"Queued {queued} transcripts for re-indexing",
        data={
            "total_found": len(transcripts),
            "queued": queued,
            "failed": failed,
        },
    )