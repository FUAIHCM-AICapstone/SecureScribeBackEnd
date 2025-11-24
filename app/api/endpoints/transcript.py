import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.jobs.tasks import process_audio_task, reindex_transcript_task
from app.models.user import User
from app.schemas.common import ApiResponse, create_pagination_meta
from app.schemas.transcript import (
    BulkTranscriptCreate,
    BulkTranscriptDelete,
    BulkTranscriptResponse,
    BulkTranscriptUpdate,
    TranscriptApiResponse,
    TranscriptCreate,
    TranscriptReindexRequest,
    TranscriptReindexResponse,
    TranscriptResponse,
    TranscriptsPaginatedResponse,
    TranscriptUpdate,
)
from app.services.audio_file import get_audio_file
from app.services.meeting import validate_meeting_for_audio_operations
from app.services.transcript import (
    bulk_create_transcripts,
    bulk_delete_transcripts,
    bulk_update_transcripts,
    create_transcript,
    delete_transcript,
    get_transcript,
    get_transcript_by_meeting,
    get_transcripts,
    update_transcript,
    validate_transcript_access,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Transcripts"])


@router.post("/transcripts/transcribe/{audio_id}", response_model=ApiResponse[dict])
def transcribe_audio_endpoint(audio_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Transcribe audio file and enqueue ASR processing."""
    try:
        # Get audio file to find meeting_id
        audio_file = get_audio_file(db, audio_id)
        if not audio_file:
            raise HTTPException(status_code=404, detail="Audio file not found")

        # Validate meeting access for audio operations
        validate_meeting_for_audio_operations(db, audio_file.meeting_id, current_user.id)

        # Enqueue Celery task for transcription
        async_result = process_audio_task.delay(str(audio_id), str(current_user.id))

        return ApiResponse(
            success=True,
            message="Audio transcription started successfully",
            data={
                "audio_file_id": str(audio_id),
                "task_id": async_result.id if async_result else None,
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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


@router.post("/meetings/{meeting_id}/transcripts/{transcript_id}/reindex", response_model=TranscriptReindexResponse)
def reindex_transcript_endpoint(
    meeting_id: uuid.UUID,
    transcript_id: uuid.UUID,
    request: TranscriptReindexRequest = TranscriptReindexRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reindex a transcript for search by regenerating vector embeddings."""
    print(f"\033[94m[reindex_transcript_endpoint] Starting reindex request for transcript {transcript_id} in meeting {meeting_id}\033[0m")
    print(f"\033[94m[reindex_transcript_endpoint] User: {current_user.id}, Force: {request.force}\033[0m")

    try:
        # Validate transcript access and relationship to meeting
        print("\033[95m[reindex_transcript_endpoint] Validating transcript access\033[0m")
        transcript = validate_transcript_access(db, transcript_id, meeting_id, current_user.id)
        print(f"\033[92m[reindex_transcript_endpoint] Access validated - transcript content length: {len(transcript.content or '')}\033[0m")

        # Enqueue Celery task for reindexing
        print("\033[94m[reindex_transcript_endpoint] Enqueueing Celery task for reindexing\033[0m")
        async_result = reindex_transcript_task.delay(str(transcript_id), str(current_user.id))
        task_id = async_result.id if async_result else None
        print(f"\033[92m[reindex_transcript_endpoint] Celery task enqueued with task_id: {task_id}\033[0m")

        return ApiResponse(
            success=True,
            message="Transcript reindex started successfully",
            data={
                "task_id": task_id,
                "transcript_id": str(transcript_id),
                "meeting_id": str(meeting_id),
                "status": "queued",
            },
        )
    except HTTPException as http_exc:
        print(f"\033[91m[reindex_transcript_endpoint] HTTP Exception: {http_exc.status_code} - {http_exc.detail}\033[0m")
        raise
    except Exception as e:
        print(f"\033[91m[reindex_transcript_endpoint] Unexpected error: {type(e).__name__}: {str(e)}\033[0m")
        raise HTTPException(status_code=400, detail=str(e))
