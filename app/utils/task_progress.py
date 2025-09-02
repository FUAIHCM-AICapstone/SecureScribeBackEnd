from datetime import datetime
from typing import Dict, Optional

from app.utils.redis import redis_client


def update_task_progress(
    task_id: str,
    user_id: str,
    progress: int,
    status: str,
    estimated_time: Optional[str] = None
) -> bool:
    """
    Update task progress in Redis with retry logic
    """
    max_retries = 3
    for attempt in range(max_retries):
        try:
            key = f"task_progress:{task_id}:{user_id}"
            data = {
                "progress": progress,
                "status": status,
                "estimated_time": estimated_time,
                "last_update": datetime.utcnow().isoformat(),
                "task_type": "test_notification"
            }

            # Store in Redis hash
            redis_client.hset(key, mapping=data)

            # Emit progress event
            emit_progress_event(task_id, user_id, data)

            return True
        except Exception as e:
            print(f"Error updating task progress (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return False
            # Wait before retry
            import time
            time.sleep(0.1 * (attempt + 1))


def get_task_progress(task_id: str, user_id: str) -> Optional[Dict]:
    """
    Get current task progress from Redis
    """
    try:
        key = f"task_progress:{task_id}:{user_id}"
        data = redis_client.hgetall(key)

        if not data:
            return None

        return {
            "task_id": task_id,
            "user_id": user_id,
            "progress": int(data.get("progress", 0)),
            "status": data.get("status", "unknown"),
            "estimated_time": data.get("estimated_time"),
            "last_update": data.get("last_update"),
            "task_type": data.get("task_type")
        }
    except Exception as e:
        print(f"Error getting task progress: {e}")
        return None


def emit_progress_event(task_id: str, user_id: str, event_data: Dict) -> bool:
    """
    Emit progress event to WebSocket connection
    """
    try:
        # Import here to avoid circular imports
        from app.services.websocket_manager import websocket_manager

        # Create WebSocket message format
        message = {
            "type": "task_progress",
            "data": {
                "task_id": task_id,
                "user_id": user_id,
                **event_data
            }
        }

        # Get the current event loop
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Broadcast to user via WebSocket
            loop.run_until_complete(websocket_manager.broadcast_to_user(user_id, message))
            print(f"Progress event emitted to WebSocket for user {user_id}: {event_data.get('status', 'unknown')}")
            return True
        finally:
            loop.close()

    except Exception as e:
        print(f"Error emitting progress event: {e}")
        return False


def cleanup_task_progress(task_id: str, user_id: str) -> bool:
    """
    Clean up task progress data from Redis
    """
    try:
        key = f"task_progress:{task_id}:{user_id}"
        redis_client.delete(key)
        return True
    except Exception as e:
        print(f"Error cleaning up task progress: {e}")
        return False
