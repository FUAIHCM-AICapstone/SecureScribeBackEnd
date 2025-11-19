import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Header, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse, create_pagination_meta
from app.schemas.meeting_bot import (
    BotWebhookCallback,
    MeetingBotCreate,
    MeetingBotJoinRequest,
    MeetingBotJoinResponse,
    MeetingBotLogCreate,
    MeetingBotLogResponse,
    MeetingBotResponse,
    MeetingBotUpdate,
)
from app.services.meeting_bot import (
    create_bot_log,
    create_meeting_bot,
    delete_meeting_bot,
    get_bot_logs,
    get_meeting_bot,
    get_meeting_bot_by_meeting,
    get_meeting_bots,
    process_bot_webhook_recording,
    trigger_meeting_bot_join,
    update_bot_status,
    update_meeting_bot,
)
from app.utils.auth import get_current_user

router = APIRouter(prefix=settings.API_V1_STR, tags=["Meeting Bot"])


@router.post("/meeting-bots", response_model=ApiResponse[MeetingBotResponse])
def create_meeting_bot_endpoint(
    bot: MeetingBotCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new meeting bot"""
    try:
        new_bot = create_meeting_bot(db, bot, current_user.id)
        return ApiResponse(
            success=True,
            message="Meeting bot created successfully",
            data=MeetingBotResponse.model_validate(new_bot),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/meeting-bots", response_model=PaginatedResponse[MeetingBotResponse])
def get_meeting_bots_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Get meeting bots with pagination"""
    try:
        bots, total = get_meeting_bots(db, current_user.id, page, limit)

        return PaginatedResponse(
            success=True,
            message="Meeting bots retrieved successfully",
            data=[MeetingBotResponse.model_validate(bot) for bot in bots],
            meta=create_pagination_meta(total, page, limit),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/meeting-bots/{bot_id}", response_model=ApiResponse[MeetingBotResponse])
def get_meeting_bot_endpoint(
    bot_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get meeting bot by ID"""
    bot = get_meeting_bot(db, bot_id, current_user.id)
    if not bot:
        raise HTTPException(status_code=404, detail="Meeting bot not found")

    return ApiResponse(
        success=True,
        message="Meeting bot retrieved successfully",
        data=MeetingBotResponse.model_validate(bot),
    )


@router.get("/meetings/{meeting_id}/bot", response_model=ApiResponse[MeetingBotResponse])
def get_meeting_bot_by_meeting_endpoint(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get meeting bot by meeting ID"""
    bot = get_meeting_bot_by_meeting(db, meeting_id, current_user.id)
    if not bot:
        raise HTTPException(status_code=404, detail="Meeting bot not found for this meeting")

    return ApiResponse(
        success=True,
        message="Meeting bot retrieved successfully",
        data=MeetingBotResponse.model_validate(bot),
    )


@router.put("/meeting-bots/{bot_id}", response_model=ApiResponse[MeetingBotResponse])
def update_meeting_bot_endpoint(
    bot_id: uuid.UUID,
    bot_data: MeetingBotUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update meeting bot"""
    try:
        updated_bot = update_meeting_bot(db, bot_id, bot_data, current_user.id)
        if not updated_bot:
            raise HTTPException(status_code=404, detail="Meeting bot not found")

        return ApiResponse(
            success=True,
            message="Meeting bot updated successfully",
            data=MeetingBotResponse.model_validate(updated_bot),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/meeting-bots/{bot_id}", response_model=ApiResponse[dict])
def delete_meeting_bot_endpoint(
    bot_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete meeting bot"""
    try:
        success = delete_meeting_bot(db, bot_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Meeting bot not found")

        return ApiResponse(
            success=True,
            message="Meeting bot deleted successfully",
            data={},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/meeting-bots/{bot_id}/logs", response_model=ApiResponse[MeetingBotLogResponse])
def create_bot_log_endpoint(
    bot_id: uuid.UUID,
    log_data: MeetingBotLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create bot log entry"""
    try:
        log = create_bot_log(db, bot_id, log_data)
        return ApiResponse(
            success=True,
            message="Bot log created successfully",
            data=MeetingBotLogResponse.model_validate(log),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/meeting-bots/{bot_id}/logs", response_model=PaginatedResponse[MeetingBotLogResponse])
def get_bot_logs_endpoint(
    bot_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    """Get bot logs with pagination"""
    try:
        logs, total = get_bot_logs(db, bot_id, page, limit)

        return PaginatedResponse(
            success=True,
            message="Bot logs retrieved successfully",
            data=[MeetingBotLogResponse.model_validate(log) for log in logs],
            meta=create_pagination_meta(total, page, limit),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/meeting-bots/{bot_id}/status", response_model=ApiResponse[MeetingBotResponse])
def update_bot_status_endpoint(
    bot_id: uuid.UUID,
    status: str,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update bot status"""
    try:
        updated_bot = update_bot_status(db, bot_id, status, error)
        if not updated_bot:
            raise HTTPException(status_code=404, detail="Meeting bot not found")

        return ApiResponse(
            success=True,
            message="Bot status updated successfully",
            data=MeetingBotResponse.model_validate(updated_bot),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/meetings/{meeting_id}/bot/join", response_model=ApiResponse[MeetingBotJoinResponse], status_code=202)
def join_meeting_bot_endpoint(
    meeting_id: uuid.UUID,
    request: MeetingBotJoinRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    authorization: Optional[str] = Header(None),
):
    """Trigger meeting bot to join a meeting"""
    try:
        print(f"\033[94m🤖 [BOT JOIN] Starting bot join for meeting {meeting_id}\033[0m")
        
        # Validate meeting_id format (UUID validation is automatic via FastAPI)

        # Extract bearer token from Authorization header
        if not authorization:
            print(f"\033[91m❌ [BOT JOIN] Missing authorization header\033[0m")
            raise HTTPException(status_code=401, detail="Authorization header required")

        # Parse bearer token (format: "Bearer {token}")
        auth_parts = authorization.split()
        if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
            print(f"\033[91m❌ [BOT JOIN] Invalid bearer token format\033[0m")
            raise HTTPException(status_code=400, detail="Invalid bearer token format")

        bearer_token = auth_parts[1]
        print(f"\033[92m✅ [BOT JOIN] Bearer token validated\033[0m")

        # Call service function to trigger bot join
        print(f"\033[93m📋 [BOT JOIN] Calling trigger_meeting_bot_join service\033[0m")
        task_info = trigger_meeting_bot_join(
            db=db,
            meeting_id=meeting_id,
            user_id=current_user.id,
            bearer_token=bearer_token,
            meeting_url_override=request.meeting_url,
            immediate=request.immediate,
        )

        # Return 202 Accepted response with task info
        print(f"\033[92m✅ [BOT JOIN] Task queued successfully - task_id: {task_info['task_id']}\033[0m")
        return ApiResponse(
            success=True,
            message="Bot join triggered successfully",
            data=MeetingBotJoinResponse(
                task_id=task_info["task_id"],
                bot_id=uuid.UUID(task_info["bot_id"]),
                meeting_id=uuid.UUID(task_info["meeting_id"]),
                status=task_info["status"],
                scheduled_start_time=task_info["scheduled_start_time"],
                created_at=task_info["created_at"],
            ),
        )
    except HTTPException:
        # Re-raise HTTPException as-is
        raise
    except Exception as e:
        print(f"\033[91m💥 [BOT JOIN] Exception occurred: {str(e)}\033[0m")
        # Catch any other exceptions and return 500
        raise HTTPException(status_code=500, detail="Failed to queue bot join task")


@router.post("/bot/webhook/recording", status_code=202)
def bot_webhook_recording_endpoint(
    recording: UploadFile = File(...),
    botId: str = Form(...),
    meetingUrl: str = Form(...),
    status: str = Form(...),
    teamId: str = Form(...),
    timestamp: str = Form(...),
    userId: str = Form(...),
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """Webhook endpoint to receive bot recording"""
    try:
        print(f"\033[94m🎥 [WEBHOOK] Received recording from bot {botId} for meeting {meetingUrl}\033[0m")
        
        # Extract bearer token from Authorization header
        if not authorization:
            print(f"\033[91m❌ [WEBHOOK] Missing authorization header\033[0m")
            raise HTTPException(status_code=401, detail="Authorization header required")

        auth_parts = authorization.split()
        if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
            print(f"\033[91m❌ [WEBHOOK] Invalid bearer token format\033[0m")
            raise HTTPException(status_code=400, detail="Invalid bearer token format")

        # Validate user via bearer token
        print(f"\033[92m✅ [WEBHOOK] Bearer token validated\033[0m")
        current_user = get_current_user(authorization)

        # Extract meeting_id from meetingUrl (format: https://meet.google.com/xxx-xxxx-xxx)
        # For now, we need to find the meeting by URL or use a different approach
        # Query meeting by URL
        from app.models.meeting import Meeting

        print(f"\033[93m📋 [WEBHOOK] Looking up meeting by URL: {meetingUrl}\033[0m")
        meeting = db.query(Meeting).filter(Meeting.url == meetingUrl).first()
        if not meeting:
            print(f"\033[91m❌ [WEBHOOK] Meeting not found for URL: {meetingUrl}\033[0m")
            raise HTTPException(status_code=404, detail="Meeting not found")

        # Read file bytes
        print(f"\033[93m📋 [WEBHOOK] Reading recording file\033[0m")
        file_bytes = recording.file.read()
        if not file_bytes:
            print(f"\033[91m❌ [WEBHOOK] Recording file is empty\033[0m")
            raise HTTPException(status_code=400, detail="Recording file is empty")

        print(f"\033[92m✅ [WEBHOOK] Recording file read successfully - size: {len(file_bytes)} bytes\033[0m")

        # Process webhook recording
        print(f"\033[93m📋 [WEBHOOK] Processing webhook recording\033[0m")
        result = process_bot_webhook_recording(
            db=db,
            meeting_id=meeting.id,
            user_id=current_user.id,
            file_bytes=file_bytes,
        )

        # Queue audio processing task
        from app.jobs.celery_worker import celery_app

        print(f"\033[93m📋 [WEBHOOK] Queuing audio processing task\033[0m")
        task = celery_app.send_task(
            "app.jobs.tasks.process_audio_task",
            args=[result["audio_file_id"], str(current_user.id)],
        )

        print(f"\033[92m✅ [WEBHOOK] Recording processed successfully - task_id: {task.id}\033[0m")
        return ApiResponse(
            success=True,
            message="Recording received and queued for processing",
            data={"task_id": task.id, "audio_file_id": result["audio_file_id"]},
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"\033[91m💥 [WEBHOOK] Exception occurred: {str(e)}\033[0m")
        # Queue retry task on failure
        from app.jobs.celery_worker import celery_app

        print(f"\033[93m📋 [WEBHOOK] Queuing retry task\033[0m")
        retry_task = celery_app.send_task(
            "app.jobs.tasks.retry_webhook_processing_task",
            args=[botId, meetingUrl, timestamp],
        )

        print(f"\033[92m✅ [WEBHOOK] Retry task queued - retry_task_id: {retry_task.id}\033[0m")
        return ApiResponse(
            success=True,
            message="Recording received, queued for retry",
            data={"retry_task_id": retry_task.id},
        )
