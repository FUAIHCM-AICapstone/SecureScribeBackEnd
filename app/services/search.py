from app.services.qdrant_service import qdrant_service
from app.utils.llm import embed_query


def init_ai_service():
    """Initialize AI service and inject into qdrant service"""
    if not qdrant_service.ai_service:
        qdrant_service.set_ai_service(embed_query)
    print("🟢 \033[92mAI service initialized\033[0m")
