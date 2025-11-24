import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.models.user import User
from app.schemas.common import ApiResponse, PaginatedResponse, create_pagination_meta
from app.schemas.meeting_bot import (
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
        from app.services.meeting_bot import serialize_meeting_bot

        new_bot = create_meeting_bot(db, bot, current_user.id)
        # Reload with meeting data
        new_bot = get_meeting_bot(db, new_bot.id, current_user.id)
        return ApiResponse(
            success=True,
            message="Meeting bot created successfully",
            data=serialize_meeting_bot(new_bot),
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
        from app.services.meeting_bot import serialize_meeting_bot

        bots, total = get_meeting_bots(db, current_user.id, page, limit)
        return PaginatedResponse(
            success=True,
            message="Meeting bots retrieved successfully",
            data=[serialize_meeting_bot(bot) for bot in bots],
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
    from app.services.meeting_bot import serialize_meeting_bot

    bot = get_meeting_bot(db, bot_id, current_user.id)
    if not bot:
        raise HTTPException(status_code=404, detail="Meeting bot not found")

    return ApiResponse(
        success=True,
        message="Meeting bot retrieved successfully",
        data=serialize_meeting_bot(bot),
    )


@router.get("/meetings/{meeting_id}/bot", response_model=ApiResponse[MeetingBotResponse])
def get_meeting_bot_by_meeting_endpoint(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get meeting bot by meeting ID"""
    from app.services.meeting_bot import serialize_meeting_bot

    bot = get_meeting_bot_by_meeting(db, meeting_id, current_user.id)
    if not bot:
        raise HTTPException(status_code=404, detail="Meeting bot not found for this meeting")

    return ApiResponse(
        success=True,
        message="Meeting bot retrieved successfully",
        data=serialize_meeting_bot(bot),
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
        from app.services.meeting_bot import serialize_meeting_bot

        updated_bot = update_meeting_bot(db, bot_id, bot_data, current_user.id)
        if not updated_bot:
            raise HTTPException(status_code=404, detail="Meeting bot not found")

        # Reload with meeting data
        updated_bot = get_meeting_bot(db, bot_id, current_user.id)
        return ApiResponse(
            success=True,
            message="Meeting bot updated successfully",
            data=serialize_meeting_bot(updated_bot),
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
        from app.services.meeting_bot import serialize_meeting_bot

        updated_bot = update_bot_status(db, bot_id, status, error)
        if not updated_bot:
            raise HTTPException(status_code=404, detail="Meeting bot not found")

        # Reload with meeting data
        updated_bot = get_meeting_bot(db, bot_id, current_user.id)
        return ApiResponse(
            success=True,
            message="Bot status updated successfully",
            data=serialize_meeting_bot(updated_bot),
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
        # Validate meeting_id format (UUID validation is automatic via FastAPI)

        # Extract bearer token from Authorization header
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")

        # Parse bearer token (format: "Bearer {token}")
        auth_parts = authorization.split()
        if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
            raise HTTPException(status_code=400, detail="Invalid bearer token format")

        bearer_token = auth_parts[1]

        # Call service function to trigger bot join
        task_info = trigger_meeting_bot_join(
            db=db,
            meeting_id=meeting_id,
            user_id=current_user.id,
            bearer_token=bearer_token,
            meeting_url_override=request.meeting_url,
            immediate=request.immediate,
        )

        # Return 202 Accepted response with task info
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
    except Exception:
        # Catch any other exceptions and return 500
        raise HTTPException(status_code=500, detail="Failed to queue bot join task")


@router.post("/bot/webhook/status", status_code=202)
def bot_webhook_status_endpoint(
    botId: str = Form(...),
    status: str = Form(...),
    error: Optional[str] = Form(None),
    actual_start_time: Optional[str] = Form(None),
    actual_end_time: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
):
    """Webhook endpoint for bot status updates during recording"""
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")

        auth_parts = authorization.split()
        if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
            raise HTTPException(status_code=400, detail="Invalid bearer token format")

        from datetime import datetime as dt

        try:
            bot_uuid = uuid.UUID(botId)

            # Parse timestamps if provided
            start_time = None
            end_time = None
            if actual_start_time:
                try:
                    start_time = dt.fromisoformat(actual_start_time.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass
            if actual_end_time:
                try:
                    end_time = dt.fromisoformat(actual_end_time.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            updated_bot = update_bot_status(
                db,
                bot_uuid,
                status,
                error,
                actual_start_time=start_time,
                actual_end_time=end_time,
            )

            if updated_bot:
                # Create bot log for status update
                log_data = MeetingBotLogCreate(
                    action="status_updated",
                    message=f"Status changed to: {status}" + (f" - {error}" if error else ""),
                )
                create_bot_log(db, bot_uuid, log_data)

                return ApiResponse(
                    success=True,
                    message="Bot status updated successfully",
                    data={"bot_id": str(bot_uuid), "status": status},
                )
            else:
                raise HTTPException(status_code=404, detail="Bot not found")

        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid botId format")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update bot status: {str(e)}")


@router.post("/bot/webhook/recording", status_code=202)
def bot_webhook_recording_endpoint(
    recording: UploadFile = File(None),
    botId: Optional[str] = Form(None),
    meetingUrl: Optional[str] = Form(None),
    status: Optional[str] = Form(None),
    error: Optional[str] = Form(None),
    actual_start_time: Optional[str] = Form(None),
    actual_end_time: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    authorization: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
):
    """Webhook endpoint to receive bot recording and update bot status"""
    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header required")

        auth_parts = authorization.split()
        if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
            raise HTTPException(status_code=400, detail="Invalid bearer token format")

        from datetime import datetime as dt

        from app.models.meeting import Meeting

        result = {}

        # Process recording if provided
        if recording and meetingUrl:
            meeting = db.query(Meeting).filter(Meeting.url == meetingUrl).first()
            if not meeting:
                raise HTTPException(status_code=404, detail="Meeting not found")

            file_bytes = recording.file.read()
            if file_bytes:
                result = process_bot_webhook_recording(
                    db=db,
                    meeting_id=meeting.id,
                    user_id=current_user.id,
                    file_bytes=file_bytes,
                )

                # Queue audio processing task
                from app.jobs.celery_worker import celery_app

                task = celery_app.send_task(
                    "app.jobs.tasks.process_audio_task",
                    args=[result["audio_file_id"], str(current_user.id)],
                )
                result["task_id"] = task.id

        # Update bot status if provided
        if botId and status:
            try:
                bot_uuid = uuid.UUID(botId)

                # Parse timestamps if provided
                start_time = None
                end_time = None
                if actual_start_time:
                    try:
                        start_time = dt.fromisoformat(actual_start_time.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass
                if actual_end_time:
                    try:
                        end_time = dt.fromisoformat(actual_end_time.replace("Z", "+00:00"))
                    except (ValueError, AttributeError):
                        pass

                updated_bot = update_bot_status(
                    db,
                    bot_uuid,
                    status,
                    error,
                    actual_start_time=start_time,
                    actual_end_time=end_time,
                )

                if updated_bot:
                    # Create bot log for status update
                    log_data = MeetingBotLogCreate(
                        action="status_updated",
                        message=f"Status changed to: {status}" + (f" - {error}" if error else ""),
                    )
                    create_bot_log(db, bot_uuid, log_data)
                    result["bot_status_updated"] = True
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid botId format")

        return ApiResponse(
            success=True,
            message="Webhook processed successfully",
            data=result,
        )
    except HTTPException:
        raise
    except Exception:
        from app.jobs.celery_worker import celery_app

        if botId and meetingUrl:
            retry_task = celery_app.send_task(
                "app.jobs.tasks.retry_webhook_processing_task",
                args=[botId, meetingUrl],
            )
            return ApiResponse(
                success=True,
                message="Webhook received, queued for retry",
                data={"retry_task_id": retry_task.id},
            )

        return ApiResponse(
            success=True,
            message="Webhook received",
            data={},
        )
