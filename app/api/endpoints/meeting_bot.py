import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.constants.messages import MessageConstants
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
from app.utils.logging import logger

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
            message=MessageConstants.MEETING_BOT_CREATED_SUCCESS,
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
            message=MessageConstants.MEETING_BOT_LIST_RETRIEVED_SUCCESS,
            data=[serialize_meeting_bot(bot) for bot in bots],
            pagination=create_pagination_meta(page, limit, total),
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
        raise HTTPException(status_code=404, detail=MessageConstants.MEETING_BOT_NOT_FOUND)

    return ApiResponse(
        success=True,
        message=MessageConstants.MEETING_BOT_RETRIEVED_SUCCESS,
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
        raise HTTPException(status_code=404, detail=MessageConstants.MEETING_BOT_NOT_FOUND)

    return ApiResponse(
        success=True,
        message=MessageConstants.MEETING_BOT_RETRIEVED_SUCCESS,
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
            raise HTTPException(status_code=404, detail=MessageConstants.MEETING_BOT_NOT_FOUND)

        # Reload with meeting data
        updated_bot = get_meeting_bot(db, bot_id, current_user.id)
        return ApiResponse(
            success=True,
            message=MessageConstants.MEETING_BOT_UPDATED_SUCCESS,
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
            raise HTTPException(status_code=404, detail=MessageConstants.MEETING_BOT_NOT_FOUND)

        return ApiResponse(
            success=True,
            message=MessageConstants.MEETING_BOT_DELETED_SUCCESS,
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
            message=MessageConstants.MEETING_BOT_LOG_CREATED_SUCCESS,
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
            message=MessageConstants.MEETING_BOT_LOG_LIST_RETRIEVED_SUCCESS,
            data=[MeetingBotLogResponse.model_validate(log) for log in logs],
            pagination=create_pagination_meta(page, limit, total),
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
            raise HTTPException(status_code=404, detail=MessageConstants.MEETING_BOT_NOT_FOUND)

        # Reload with meeting data
        updated_bot = get_meeting_bot(db, bot_id, current_user.id)
        return ApiResponse(
            success=True,
            message=MessageConstants.MEETING_BOT_UPDATED_SUCCESS,
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
            raise HTTPException(status_code=401, detail=MessageConstants.AUTHORIZATION_HEADER_REQUIRED)

        # Parse bearer token (format: "Bearer {token}")
        auth_parts = authorization.split()
        if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
            raise HTTPException(status_code=400, detail=MessageConstants.INVALID_BEARER_TOKEN_FORMAT)

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
            message=MessageConstants.MEETING_BOT_JOIN_TRIGGERED_SUCCESS,
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
        raise HTTPException(status_code=500, detail=MessageConstants.MEETING_BOT_JOIN_FAILED)


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
    logger.info("[WEBHOOK_STATUS] BOT STATUS WEBHOOK STARTED")
    logger.info(f"[WEBHOOK_STATUS] Received request with botId: {botId}, status: {status}")

    try:
        logger.debug("[WEBHOOK_STATUS] Step 1: Validating authorization header")
        if not authorization:
            logger.error("[WEBHOOK_STATUS] ERROR: Authorization header missing")
            raise HTTPException(status_code=401, detail=MessageConstants.AUTHORIZATION_HEADER_REQUIRED)

        auth_parts = authorization.split()
        if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
            logger.error("[WEBHOOK_STATUS] ERROR: Invalid bearer token format")
            raise HTTPException(status_code=400, detail=MessageConstants.INVALID_BEARER_TOKEN_FORMAT)

        logger.info("[WEBHOOK_STATUS] Authorization validation passed")

        logger.debug("[WEBHOOK_STATUS] Step 2: Parsing bot UUID")
        try:
            bot_uuid = uuid.UUID(botId)
            logger.info(f"[WEBHOOK_STATUS] Bot UUID parsed successfully: {bot_uuid}")
        except ValueError as e:
            logger.error(f"[WEBHOOK_STATUS] ERROR: Invalid bot UUID format: {e}")
            raise HTTPException(status_code=400, detail=MessageConstants.INVALID_REQUEST)

        logger.debug("[WEBHOOK_STATUS] Step 3: Parsing timestamps")
        # Parse timestamps if provided
        start_time = None
        end_time = None
        if actual_start_time:
            try:
                from datetime import datetime

                start_time = datetime.fromisoformat(actual_start_time.replace("Z", "+00:00"))
                logger.info(f"[WEBHOOK_STATUS] Start time parsed: {start_time}")
            except (ValueError, AttributeError) as e:
                logger.warning(f"[WEBHOOK_STATUS] WARNING: Could not parse start time '{actual_start_time}': {e}")
        else:
            logger.debug("[WEBHOOK_STATUS] No start time provided")

        if actual_end_time:
            try:
                from datetime import datetime

                end_time = datetime.fromisoformat(actual_end_time.replace("Z", "+00:00"))
                logger.info(f"[WEBHOOK_STATUS] End time parsed: {end_time}")
            except (ValueError, AttributeError) as e:
                logger.warning(f"[WEBHOOK_STATUS] WARNING: Could not parse end time '{actual_end_time}': {e}")
        else:
            logger.debug("[WEBHOOK_STATUS] No end time provided")

        logger.debug("[WEBHOOK_STATUS] Step 4: Updating bot status in database")
        updated_bot = update_bot_status(
            db,
            bot_uuid,
            status,
            error,
            actual_start_time=start_time,
            actual_end_time=end_time,
        )

        if updated_bot:
            logger.info(f"[WEBHOOK_STATUS] Bot status updated successfully to: {status}")

            logger.debug("[WEBHOOK_STATUS] Step 5: Creating bot log entry")
            # Create bot log for status update
            log_data = MeetingBotLogCreate(
                action="status_updated",
                message=f"Status changed to: {status}" + (f" - {error}" if error else ""),
            )
            create_bot_log(db, bot_uuid, log_data)
            logger.info("[WEBHOOK_STATUS] Bot log created successfully")

            logger.info("[WEBHOOK_STATUS] BOT STATUS WEBHOOK COMPLETED SUCCESSFULLY")
            return ApiResponse(
                success=True,
                message=MessageConstants.MEETING_BOT_UPDATED_SUCCESS,
                data={"bot_id": str(bot_uuid), "status": status},
            )
        else:
            logger.error(f"[WEBHOOK_STATUS] ERROR: Bot not found with ID: {bot_uuid}")
            raise HTTPException(status_code=404, detail=MessageConstants.MEETING_BOT_NOT_FOUND)

    except HTTPException:
        logger.error("[WEBHOOK_STATUS] HTTPException raised, re-raising")
        raise
    except Exception as e:
        logger.error(f"[WEBHOOK_STATUS] UNEXPECTED ERROR: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=MessageConstants.INTERNAL_SERVER_ERROR)


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
    logger.info("[WEBHOOK_RECORDING] BOT RECORDING WEBHOOK STARTED")
    logger.info(f"[WEBHOOK_RECORDING] Received request - recording: {recording is not None}, botId: {botId}, meetingUrl: {meetingUrl}, status: {status}")

    try:
        logger.debug("[WEBHOOK_RECORDING] Step 1: Validating authorization header")
        if not authorization:
            logger.error("[WEBHOOK_RECORDING] ERROR: Authorization header missing")
            raise HTTPException(status_code=401, detail=MessageConstants.AUTHORIZATION_HEADER_REQUIRED)

        auth_parts = authorization.split()
        if len(auth_parts) != 2 or auth_parts[0].lower() != "bearer":
            logger.error("[WEBHOOK_RECORDING] ERROR: Invalid bearer token format")
            raise HTTPException(status_code=400, detail=MessageConstants.INVALID_BEARER_TOKEN_FORMAT)

        logger.info("[WEBHOOK_RECORDING] Authorization validation passed")

        from app.services.meeting import get_meeting_by_url

        result = {}
        logger.debug(f"[WEBHOOK_RECORDING] Step 2: Processing recording upload (recording present: {recording is not None})")

        # Process recording if provided
        if recording and meetingUrl:
            logger.info(f"[WEBHOOK_RECORDING] Recording file detected: {recording.filename}, size: {getattr(recording, 'size', 'unknown')}")

            logger.debug("[WEBHOOK_RECORDING] Step 2.1: Finding meeting by URL")
            meeting = get_meeting_by_url(db, meetingUrl)
            if not meeting:
                logger.error(f"[WEBHOOK_RECORDING] ERROR: Meeting not found for URL: {meetingUrl}")
                raise HTTPException(status_code=404, detail=MessageConstants.MEETING_NOT_FOUND)

            logger.info(f"[WEBHOOK_RECORDING] Meeting found: {meeting.id}")

            logger.debug("[WEBHOOK_RECORDING] Step 2.2: Reading recording file bytes")
            file_bytes = recording.file.read()
            file_size = len(file_bytes)
            logger.info(f"[WEBHOOK_RECORDING] File read successfully: {file_size} bytes")

            if file_bytes:
                logger.debug("[WEBHOOK_RECORDING] Step 2.3: Processing bot webhook recording")
                result = process_bot_webhook_recording(
                    db=db,
                    meeting_id=meeting.id,
                    user_id=current_user.id,
                    file_bytes=file_bytes,
                )
                logger.info(f"[WEBHOOK_RECORDING] Recording processed successfully, audio_file_id: {result.get('audio_file_id')}")

                logger.debug("[WEBHOOK_RECORDING] Step 2.4: Queueing audio processing task")
                # Queue audio processing task
                from app.jobs.celery_worker import celery_app

                task = celery_app.send_task(
                    "app.jobs.tasks.process_audio_task",
                    args=[result["audio_file_id"], str(current_user.id)],
                )
                result["task_id"] = task.id
                logger.info(f"[WEBHOOK_RECORDING] Audio processing task queued: {task.id}")
            else:
                logger.warning("[WEBHOOK_RECORDING] WARNING: Recording file is empty")
        else:
            logger.debug("[WEBHOOK_RECORDING] No recording or meeting URL provided, skipping recording processing")

        logger.debug(f"[WEBHOOK_RECORDING] Step 3: Processing bot status update (botId present: {botId is not None}, status present: {status is not None})")
        # Update bot status if provided
        if botId and status:
            logger.info(f"[WEBHOOK_RECORDING] Processing status update for bot: {botId}")

            try:
                bot_uuid = uuid.UUID(botId)
                logger.info(f"[WEBHOOK_RECORDING] Bot UUID parsed: {bot_uuid}")

                logger.debug("[WEBHOOK_RECORDING] Step 3.1: Parsing timestamps for status update")
                # Parse timestamps if provided
                start_time = None
                end_time = None
                if actual_start_time:
                    try:
                        from datetime import datetime

                        start_time = datetime.fromisoformat(actual_start_time.replace("Z", "+00:00"))
                        logger.info(f"[WEBHOOK_RECORDING] Start time parsed: {start_time}")
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"[WEBHOOK_RECORDING] WARNING: Could not parse start time '{actual_start_time}': {e}")
                if actual_end_time:
                    try:
                        from datetime import datetime

                        end_time = datetime.fromisoformat(actual_end_time.replace("Z", "+00:00"))
                        logger.info(f"[WEBHOOK_RECORDING] End time parsed: {end_time}")
                    except (ValueError, AttributeError) as e:
                        logger.warning(f"[WEBHOOK_RECORDING] WARNING: Could not parse end time '{actual_end_time}': {e}")

                logger.debug("[WEBHOOK_RECORDING] Step 3.2: Updating bot status in database")
                updated_bot = update_bot_status(
                    db,
                    bot_uuid,
                    status,
                    error,
                    actual_start_time=start_time,
                    actual_end_time=end_time,
                )

                if updated_bot:
                    logger.info(f"[WEBHOOK_RECORDING] Bot status updated to: {status}")

                    logger.debug("[WEBHOOK_RECORDING] Step 3.3: Creating bot log entry")
                    # Create bot log for status update
                    log_data = MeetingBotLogCreate(
                        action="status_updated",
                        message=f"Status changed to: {status}" + (f" - {error}" if error else ""),
                    )
                    create_bot_log(db, bot_uuid, log_data)
                    logger.info("[WEBHOOK_RECORDING] Bot log created successfully")
                    result["bot_status_updated"] = True
                else:
                    logger.error(f"[WEBHOOK_RECORDING] ERROR: Bot not found: {bot_uuid}")

            except ValueError as e:
                logger.error(f"[WEBHOOK_RECORDING] ERROR: Invalid bot UUID format: {e}")
                raise HTTPException(status_code=400, detail=MessageConstants.INVALID_REQUEST)
        else:
            logger.debug("[WEBHOOK_RECORDING] No bot status update requested")

        logger.info("[WEBHOOK_RECORDING] BOT RECORDING WEBHOOK COMPLETED SUCCESSFULLY")
        logger.info(f"[WEBHOOK_RECORDING] Result summary: {result}")
        return ApiResponse(
            success=True,
            message=MessageConstants.MEETING_BOT_WEBHOOK_PROCESSED_SUCCESS,
            data=result,
        )
    except HTTPException:
        logger.error("[WEBHOOK_RECORDING] HTTPException raised, re-raising")
        raise
    except Exception as e:
        logger.error(f"[WEBHOOK_RECORDING] UNEXPECTED ERROR: {type(e).__name__}: {str(e)}")
        logger.warning("[WEBHOOK_RECORDING] Attempting retry mechanism")

        from app.jobs.celery_worker import celery_app

        if botId and meetingUrl:
            logger.info("[WEBHOOK_RECORDING] Queueing retry task")
            retry_task = celery_app.send_task(
                "app.jobs.tasks.retry_webhook_processing_task",
                args=[botId, meetingUrl],
            )
            logger.info(f"[WEBHOOK_RECORDING] Retry task queued: {retry_task.id}")
            return ApiResponse(
                success=True,
                message=MessageConstants.MEETING_BOT_WEBHOOK_QUEUED_FOR_RETRY,
                data={"retry_task_id": retry_task.id},
            )

        logger.warning("[WEBHOOK_RECORDING] No retry possible, returning basic success response")
        return ApiResponse(
            success=True,
            message=MessageConstants.MEETING_BOT_WEBHOOK_RECEIVED,
            data={},
        )
