import asyncio
import time

from celery import Celery

from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.utils.redis import publish_to_user_channel
from app.utils.task_progress import update_task_progress

initialize_firebase()

celery_app = Celery(
    "worker", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND
)


def publish_task_progress_sync(
    user_id: str,
    progress: int,
    status: str,
    estimated_time: str = None,
    task_type: str = "test_notification",
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
            message = {
                "type": "task_progress",
                "data": {
                    "progress": progress,
                    "status": status,
                    "estimated_time": estimated_time or "",
                    "task_type": task_type,
                    "timestamp": time.time(),
                },
            }

            # Publish to Redis channel
            success = loop.run_until_complete(publish_to_user_channel(user_id, message))

            if success:
                return True
            else:
                print(
                    f"Failed to publish task progress for user {user_id} (attempt {attempt + 1}/{max_retries})"
                )
                if attempt < max_retries - 1:
                    time.sleep(base_delay * (2**attempt))  # Exponential backoff

        except Exception as e:
            print(
                f"Error publishing task progress for user {user_id} (attempt {attempt + 1}/{max_retries}): {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(base_delay * (2**attempt))  # Exponential backoff

    return False


@celery_app.task(bind=True)
def send_test_notification_task(self, user_id: str):
    task_id = self.request.id or f"test_task_{user_id}_{int(time.time())}"
    publish_success_count = 0
    total_publish_attempts = 6

    try:
        # Step 1: Started
        update_task_progress(task_id, user_id, 0, "started")
        if publish_task_progress_sync(
            user_id, 0, "started", "30s", "test_notification"
        ):
            publish_success_count += 1
        print("started")
        time.sleep(1)

        # Step 2: Processing
        update_task_progress(task_id, user_id, 25, "processing", "25s")
        if publish_task_progress_sync(
            user_id, 25, "processing", "25s", "test_notification"
        ):
            publish_success_count += 1
        print("processing")
        time.sleep(1)

        # Step 3: Database work
        update_task_progress(task_id, user_id, 50, "database", "15s")
        if publish_task_progress_sync(
            user_id, 50, "database", "15s", "test_notification"
        ):
            publish_success_count += 1
        print("database")
        time.sleep(1)

        # Step 4: Creating notification
        update_task_progress(task_id, user_id, 75, "creating_notification", "10s")
        if publish_task_progress_sync(
            user_id, 75, "creating_notification", "10s", "test_notification"
        ):
            publish_success_count += 1
        print("creating_notification")
        time.sleep(1)

        # Step 5: Sending FCM
        update_task_progress(task_id, user_id, 90, "sending_fcm", "5s")
        if publish_task_progress_sync(
            user_id, 90, "sending_fcm", "5s", "test_notification"
        ):
            publish_success_count += 1
        print("sending_fcm")
        time.sleep(1)

        # Step 6: Completed
        update_task_progress(task_id, user_id, 100, "completed")
        if publish_task_progress_sync(
            user_id, 100, "completed", "", "test_notification"
        ):
            publish_success_count += 1
        print(
            f"completed (Redis publish: {publish_success_count}/{total_publish_attempts})"
        )
        return {
            "status": "ok",
            "redis_publish_success": publish_success_count,
            "redis_publish_total": total_publish_attempts,
        }
    except Exception as exc:
        # Publish failure state
        update_task_progress(task_id, user_id, 0, "failed")
        publish_task_progress_sync(user_id, 0, "failed", "", "test_notification")
        print(f"Task failed: {exc}")
        raise
