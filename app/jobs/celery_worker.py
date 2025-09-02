import time
from uuid import UUID

from celery import Celery

from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.db import SessionLocal
from app.services.notification import create_notification, send_fcm_notification

# Initialize Firebase for Celery worker
initialize_firebase()

celery_app = Celery(
    "worker", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND
)


@celery_app.task
def send_test_notification_task(user_id: str):
    print("Running...")
    time.sleep(5)  # Wait 30 seconds as mentioned in the notification
    db = SessionLocal()
    try:
        user_uuid = UUID(user_id)
        create_notification(
            db,
            user_id=user_uuid,
            type="test",
            payload={"title": "TaskCompleted", "body": "Task is done after 30s"}		,
            channel="fcm",
        )
        try:
            send_fcm_notification(
                [user_uuid],
                "Task Completed",
                "Your 30-second test task has finished successfully!",
                {"type": "task_complete", "task": "test_30s"},
            )
        except Exception as e:
            print("Error sending FCM notification:", e)
    finally:
        db.close()
