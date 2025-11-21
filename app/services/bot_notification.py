import asyncio
import logging
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.meeting import Meeting, MeetingBot
from app.utils.redis import publish_to_user_channel

logger = logging.getLogger(__name__)


async def send_bot_status_notification(
    db: Session,
    bot_id: UUID,
    status: str,
    error: Optional[str] = None,
) -> bool:
    """
    Send bot status notification via WebSocket and FCM.
    Only sends notifications for key status transitions: recording, complete, error
    Sends to bot creator only.
    """
    try:
        # Fetch bot with meeting details
        bot = (
            db.query(MeetingBot)
            .filter(MeetingBot.id == bot_id)
            .first()
        )

        if not bot:
            logger.warning("Bot not found for notification: %s", bot_id)
            return False

        # Only notify on key statuses
        if status not in ["recording", "complete", "error"]:
            logger.debug("Skipping notification for status: %s", status)
            return True

        # Fetch meeting data
        meeting = db.query(Meeting).filter(Meeting.id == bot.meeting_id).first()
        if not meeting:
            logger.warning("Meeting not found for bot notification: %s", bot.meeting_id)
            return False

        # Prepare notification payload
        notification_data = {
            "type": "bot_status_update",
            "data": {
                "bot_id": str(bot_id),
                "status": status,
                "meeting_id": str(bot.meeting_id),
                "meeting_title": meeting.title or "Untitled Meeting",
                "meeting_url": meeting.url,
                "actual_start_time": bot.actual_start_time.isoformat() if bot.actual_start_time else None,
                "actual_end_time": bot.actual_end_time.isoformat() if bot.actual_end_time else None,
                "error": error,
                "created_by": str(bot.created_by),
                "retry_count": bot.retry_count,
                "last_error": bot.last_error,
                "timestamp": bot.updated_at.isoformat() if bot.updated_at else None,
            },
        }

        # Send WebSocket notification via Redis
        creator_id = str(bot.created_by)
        logger.info(
            "Sending bot status notification to user %s (bot=%s, status=%s)",
            creator_id,
            bot_id,
            status,
        )

        ws_success = await publish_to_user_channel(creator_id, notification_data)

        # Send FCM notification asynchronously (don't block on FCM)
        asyncio.create_task(
            _send_fcm_notification_async(bot.created_by, status, meeting.title, error)
        )

        return ws_success

    except Exception as e:
        logger.exception("Failed to send bot status notification: %s", e)
        return False


async def _send_fcm_notification_async(
    user_id: UUID,
    status: str,
    meeting_title: str,
    error: Optional[str] = None,
) -> None:
    """
    Send FCM notification asynchronously without blocking.
    """
    try:
        from app.services.notification import send_fcm_notification

        # Map status to user-friendly titles
        status_titles = {
            "recording": "Recording Started",
            "complete": "Recording Complete",
            "error": "Recording Failed",
        }

        status_bodies = {
            "recording": f"Bot started recording meeting: {meeting_title}",
            "complete": f"Bot finished recording meeting: {meeting_title}",
            "error": f"Bot failed to record meeting: {meeting_title}" + (f" - {error}" if error else ""),
        }

        title = status_titles.get(status, "Bot Status Update")
        body = status_bodies.get(status, f"Meeting bot status: {status}")

        logger.info("Sending FCM notification to user %s (status=%s)", user_id, status)

        send_fcm_notification(
            user_ids=[user_id],
            title=title,
            body=body,
            data={
                "bot_status": status,
                "meeting_title": meeting_title,
                "type": "bot_status_update",
            },
            icon="https://cdn-icons-png.flaticon.com/512/1995/1995473-camera.png",
        )

        logger.info("FCM notification sent successfully to user %s", user_id)

    except Exception as e:
        logger.exception("Failed to send FCM notification to user %s: %s", user_id, e)
