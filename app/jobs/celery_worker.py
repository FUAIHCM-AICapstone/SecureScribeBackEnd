import time

from celery import Celery

from app.core.config import settings
from app.core.firebase import initialize_firebase
from app.core.vault_loader import load_config_from_api_v2
from app.utils.logging import setup_logging
from app.utils.redis import publish_to_user_channel  # noqa: F401
from app.utils.task_progress import publish_task_progress_sync, update_task_progress

load_config_from_api_v2()
initialize_firebase()
setup_logging(settings.LOG_LEVEL)

celery_app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.jobs.tasks"],  # Explicitly include tasks module
)

# Configure Celery settings for better timeout handling
celery_app.conf.update(
    # Task timeout settings
    task_soft_time_limit=30000,
    task_time_limit=60000,
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50,
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
)


@celery_app.task(bind=True)
def send_test_notification_task(self, user_id: str):
    task_id = self.request.id or f"test_task_{user_id}_{int(time.time())}"
    publish_success_count = 0
    total_publish_attempts = 6

    try:
        # Step 1: Started
        update_task_progress(task_id, user_id, 0, "started")
        if publish_task_progress_sync(user_id, 0, "started", "30s", "test_notification", task_id):
            publish_success_count += 1
        time.sleep(1)

        # Step 2: Processing
        update_task_progress(task_id, user_id, 25, "processing", "25s")
        if publish_task_progress_sync(user_id, 25, "processing", "25s", "test_notification", task_id):
            publish_success_count += 1
        time.sleep(1)

        # Step 3: Database work
        update_task_progress(task_id, user_id, 50, "database", "15s")
        if publish_task_progress_sync(user_id, 50, "database", "15s", "test_notification", task_id):
            publish_success_count += 1
        time.sleep(1)

        # Step 4: Creating notification
        update_task_progress(task_id, user_id, 75, "creating_notification", "10s")
        if publish_task_progress_sync(user_id, 75, "creating_notification", "10s", "test_notification", task_id):
            publish_success_count += 1
        time.sleep(1)

        # Step 5: Sending FCM
        update_task_progress(task_id, user_id, 90, "sending_fcm", "5s")
        if publish_task_progress_sync(user_id, 90, "sending_fcm", "5s", "test_notification", task_id):
            publish_success_count += 1
        time.sleep(1)

        # Step 6: Completed
        update_task_progress(task_id, user_id, 100, "completed")
        if publish_task_progress_sync(user_id, 100, "completed", "", "test_notification", task_id):
            publish_success_count += 1
        return {
            "status": "ok",
            "redis_publish_success": publish_success_count,
            "redis_publish_total": total_publish_attempts,
        }
    except Exception as exc:
        # Publish failure state
        print(f"[Celery] send_test_notification_task failed: {exc}")
        update_task_progress(task_id, user_id, 0, "failed")
        publish_task_progress_sync(user_id, 0, "failed", "", "test_notification", task_id)
        raise
