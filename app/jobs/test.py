import requests
from app.core.config import settings
from app.jobs.celery_worker import celery_app

@celery_app.task(bind=True)
def ping_bot_api_task(self):
    """Simple task to ping bot API"""
    try:
        url = f"{settings.BOT_SERVICE_URL}/ping"
        response = requests.get(url, timeout=10)
        return {"success": True, "status_code": response.status_code, "response": response.text}
    except Exception as e:
        return {"success": False, "error": str(e)}
