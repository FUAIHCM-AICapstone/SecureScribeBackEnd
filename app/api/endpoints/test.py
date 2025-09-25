from fastapi import APIRouter, BackgroundTasks
from app.jobs.celery_worker import celery_app
from app.jobs.test import ping_bot_api_task

router = APIRouter()

@router.post("/test-bot-ping")
async def test_bot_ping():
    """Test bot API connectivity via Celery"""
    task = ping_bot_api_task.delay()
    return {"task_id": task.id, "status": "queued"}

@router.get("/test-bot-result/{task_id}")
async def get_bot_test_result(task_id: str):
    """Get result of bot API test"""
    task = celery_app.AsyncResult(task_id)
    if task.ready():
        return {"task_id": task_id, "status": "completed", "result": task.result}
    return {"task_id": task_id, "status": "pending"}
