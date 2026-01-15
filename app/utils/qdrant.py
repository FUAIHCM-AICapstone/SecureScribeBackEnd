import logging

from qdrant_client import QdrantClient

from app.core.config import settings

logger = logging.getLogger(__name__)


class QdrantClientManager:
    """Qdrant client manager for centralized connection management with error resilience."""

    def __init__(self):
        self._client = None
        self._connection_attempts = 0
        self._max_retries = 3

    def get_client(self) -> QdrantClient:
        """Get or create Qdrant client instance with retry logic.

        Attempts to establish connection with exponential backoff.
        Supports both local and cloud instances with optional API key.
        Raises exception if all retries fail.
        """
        if self._client is not None:
            return self._client

        attempt = 0
        last_error = None

        while attempt < self._max_retries:
            try:
                attempt += 1
                print(f"\033[94m[QDRANT] Attempting connection (attempt {attempt}/{self._max_retries})\033[0m")

                # Build client kwargs based on whether API key is set
                client_kwargs = {"timeout": 30.0}
                if settings.QDRANT_API_KEY:
                    # Cloud instance with API key
                    client_kwargs["url"] = f"https://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}"
                    client_kwargs["api_key"] = settings.QDRANT_API_KEY
                    print("\033[94m[QDRANT] Using cloud instance with API key\033[0m")
                else:
                    # Local instance without API key
                    client_kwargs["host"] = settings.QDRANT_HOST
                    client_kwargs["port"] = 6333  # HTTP REST API port
                    client_kwargs["prefer_grpc"] = False
                    print("\033[94m[QDRANT] Using local instance\033[0m")

                self._client = QdrantClient(**client_kwargs)

                # Test connection by listing collections
                self._client.get_collections()
                print("\033[92m[QDRANT] Client connected successfully\033[0m")
                return self._client

            except Exception as connection_error:
                last_error = connection_error
                self._client = None
                error_msg = f"Connection attempt {attempt} failed: {type(connection_error).__name__}: {str(connection_error)}"
                print(f"\033[93m[QDRANT] {error_msg}\033[0m")
                logger.warning(error_msg)

                if attempt < self._max_retries:
                    import time

                    wait_time = 2 ** (attempt - 1)  # Exponential backoff: 1s, 2s, 4s
                    print(f"\033[94m[QDRANT] Retrying in {wait_time}s...\033[0m")
                    time.sleep(wait_time)

        # All retries exhausted
        error_msg = f"Failed to connect to Qdrant after {self._max_retries} attempts: {last_error}"
        print(f"\033[91m[QDRANT] {error_msg}\033[0m")
        logger.error(error_msg)
        raise ConnectionError(error_msg) from last_error

    def health_check(self) -> bool:
        """Check if Qdrant is healthy.

        Returns:
            bool: True if connection is healthy, False otherwise.
        """
        try:
            client = self.get_client()
            # Try to list collections to check connection
            client.get_collections()
            return True
        except Exception as e:
            print(f"\033[91m[QDRANT] Health check failed: {str(e)}\033[0m")
            logger.error(f"Qdrant health check failed: {e}")
            # Reset client on failure so next call will retry
            self._client = None
            return False

    def get_collection_info(self, collection_name: str = "documents"):
        """Get information about a collection.

        Args:
            collection_name: Name of the collection to query.

        Returns:
            Collection info dict or None if not found.
        """
        try:
            client = self.get_client()
            return client.get_collection(collection_name)
        except Exception as e:
            print(f"\033[91m[QDRANT] Failed to get collection info: {str(e)}\033[0m")
            logger.error(f"Failed to get collection {collection_name}: {e}")
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
