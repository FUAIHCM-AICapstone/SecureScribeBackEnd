import time
from uuid import UUID

from celery import Celery

from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.db import SessionLocal
from app.services.notification import create_notification, send_fcm_notification
from app.utils.task_progress import update_task_progress, cleanup_task_progress

# Initialize Firebase for Celery worker
initialize_firebase()

celery_app = Celery(
    "worker", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND
)


@celery_app.task(bind=True)
def send_test_notification_task(self, user_id: str):
    task_id = self.request.id or f"test_task_{user_id}_{int(time.time())}"

    print(f"Running task {task_id}...")

    # Progress 0% - Task started
    update_task_progress(task_id, user_id, 0, "started")

    time.sleep(15)  # First 15 seconds

    # Progress 50% - Processing
    update_task_progress(task_id, user_id, 50, "processing", "15s")

    time.sleep(15)  # Remaining 15 seconds

    db = SessionLocal()
    try:
        user_uuid = UUID(user_id)

        # Progress 75% - Creating notification
        update_task_progress(task_id, user_id, 75, "creating_notification", "5s")

        create_notification(
            db,
            user_id=user_uuid,
            type="test",
            payload={"title": "TaskCompleted", "body": "Task is done after 30s"}		,
            channel="fcm",
        )

        # Progress 90% - Sending FCM notification
        update_task_progress(task_id, user_id, 90, "sending_fcm", "2s")

        try:
            send_fcm_notification(
                [user_uuid],
                "Task Completed",
                "Your 30-second test task has finished successfully!",
                {"type": "task_complete", "task": "test_30s"},
            )
        except Exception as e:
            print("Error sending FCM notification:", e)

        # Progress 100% - Completed
        update_task_progress(task_id, user_id, 100, "completed")

        # Cleanup after completion
        cleanup_task_progress(task_id, user_id)

    except Exception as e:
        # Mark task as failed
        update_task_progress(task_id, user_id, 0, "failed")
        print(f"Task {task_id} failed: {e}")
        raise
    finally:
        db.close()
