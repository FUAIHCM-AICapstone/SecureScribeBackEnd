from qdrant_client import QdrantClient

from app.core.config import settings


class QdrantClientManager:
    """Qdrant client manager for centralized connection management"""

    def __init__(self):
        self._client = None

    def get_client(self) -> QdrantClient:
        """Get or create Qdrant client instance"""
        if self._client is None:
            self._client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT, timeout=30.0)
            print("🟢 \033[92mQdrant client connected\033[0m")
        return self._client

    def health_check(self) -> bool:
        """Check if Qdrant is healthy"""
        try:
            client = self.get_client()
            # Try to list collections to check connection
            client.get_collections()
            return True
        except Exception:
            return False

    def get_collection_info(self, collection_name: str = "documents"):
        """Get information about a collection"""
        try:
            client = self.get_client()
            return client.get_collection(collection_name)
        except Exception:
            return None


# Global instance
qdrant_client_manager = QdrantClientManager()


def get_qdrant_client() -> QdrantClient:
    """Get the global Qdrant client instance"""
    return qdrant_client_manager.get_client()


def health_check() -> bool:
    """Check Qdrant health"""
    return qdrant_client_manager.health_check()


def get_collection_info(collection_name: str = "documents"):
    """Get collection information"""
    return qdrant_client_manager.get_collection_info(collection_name)
