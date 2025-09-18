# app/utils/task_progress.py
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from app.utils.redis import get_redis_client, publish_to_user_channel

logger = logging.getLogger(__name__)

# TTL cho last state (ví dụ giữ 1 giờ) — ephemeral requirement
TASK_PROGRESS_TTL_SECONDS = 60 * 60  # 1 hour


def normalize_user_id(user_id: str | UUID) -> str:
    if isinstance(user_id, UUID):
        return str(user_id)
    return str(user_id)


def publish_task_progress(user_id: str, payload: dict) -> bool:
    """
    Publish to user's channel. Uses Redis pub/sub.
    Return True if published (or at least attempted).
    """
    try:
        r = get_redis_client()
        channel = f"user_progress:{user_id}"
        # publish returns number of subscribers (may be 0)
        num = r.publish(channel, json.dumps(payload))
        logger.debug("Published to %s (subscribers=%s): %s", channel, num, payload)
        return True
    except Exception as e:
        logger.exception("Failed to publish task progress for user %s: %s", user_id, e)
        # don't raise to avoid crashing workers
        return False


def update_task_progress(
    task_id: str,
    user_id: str | UUID,
    progress: int,
    status: str,
    estimated_time: Optional[str] = None,
    task_type: str = "test_notification",
) -> bool:
    """Update task progress in Redis and publish to WebSocket"""
    normalized_user_id = normalize_user_id(user_id)
    logger.info(
        "Updating task progress for task_id=%s user_id=%s progress=%s status=%s",
        task_id,
        normalized_user_id,
        progress,
        status,
    )
    try:
        r = get_redis_client()
        key = f"task_progress:{task_id}:{normalized_user_id}"
        data = {
            "task_id": task_id,
            "progress": int(progress),
            "status": status,
            "estimated_time": estimated_time or "",
            "last_update": datetime.utcnow().isoformat() + "Z",
            "task_type": task_type,
        }

        # store last-state as hash, set TTL so ephemeral
        r.hset(key, mapping=data)
        r.expire(key, TASK_PROGRESS_TTL_SECONDS)

        publish_task_progress(
            normalized_user_id,
            {"type": "task_progress", "data": data},
        )

        return True
    except Exception as e:
        logger.exception("update_task_progress failed for task %s user %s: %s", task_id, user_id, e)
        return False


def publish_task_progress_sync(
    user_id: str,
    progress: int,
    status: str,
    estimated_time: str = None,
    task_type: str = "test_notification",
    task_id: str = None,
) -> bool:
    """
    Synchronous wrapper to publish task progress to Redis pub/sub.
    Since Celery tasks are synchronous, we need to create an event loop.
    Returns True if successful, False otherwise.
    """
    max_retries = 3
    base_delay = 0.2

    for attempt in range(max_retries):
        try:
            # Create event loop if one doesn't exist
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Prepare message
            message_data = {
                "progress": progress,
                "status": status,
                "estimated_time": estimated_time or "",
                "task_type": task_type,
                "timestamp": time.time(),
            }

            # Include task_id if provided
            if task_id:
                message_data["task_id"] = task_id

            message = {
                "type": "task_progress",
                "data": message_data,
            }

            # Publish to Redis channel
            success = loop.run_until_complete(publish_to_user_channel(user_id, message))

            if success:
                return True
            else:
                logger.warning(
                    "Failed to publish task progress for user %s (attempt %d/%d)",
                    user_id,
                    attempt + 1,
                    max_retries,
                )
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2**attempt))  # Exponential backoff

        except Exception as e:
            logger.exception(
                "Error publishing task progress for user %s (attempt %d/%d): %s",
                user_id,
                attempt + 1,
                max_retries,
                e,
            )
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2**attempt))  # Exponential backoff

    return False
