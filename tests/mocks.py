"""Mock objects for external services"""

from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock


class MockMinIOClient:
    """Mock MinIO client for testing file storage operations"""

    def __init__(self):
        self.storage: Dict[str, bytes] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: Any,
        length: int = -1,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, str]] = None,
    ) -> None:
        """Mock put_object - stores file in memory"""
        key = f"{bucket_name}/{object_name}"
        if isinstance(data, bytes):
            self.storage[key] = data
        else:
            self.storage[key] = data.read() if hasattr(data, "read") else bytes(data)
        if metadata:
            self.metadata[key] = metadata

    def get_object(self, bucket_name: str, object_name: str) -> MagicMock:
        """Mock get_object - retrieves file from memory"""
        key = f"{bucket_name}/{object_name}"
        mock_response = MagicMock()
        mock_response.data = self.storage.get(key, b"")
        mock_response.read = lambda: self.storage.get(key, b"")
        return mock_response

    def remove_object(self, bucket_name: str, object_name: str) -> None:
        """Mock remove_object - deletes file from memory"""
        key = f"{bucket_name}/{object_name}"
        if key in self.storage:
            del self.storage[key]
        if key in self.metadata:
            del self.metadata[key]

    def list_objects(self, bucket_name: str, prefix: str = "") -> List[MagicMock]:
        """Mock list_objects - lists files in memory"""
        results = []
        for key in self.storage.keys():
            if key.startswith(f"{bucket_name}/{prefix}"):
                mock_obj = MagicMock()
                mock_obj.object_name = key.replace(f"{bucket_name}/", "")
                mock_obj.size = len(self.storage[key])
                results.append(mock_obj)
        return results

    def bucket_exists(self, bucket_name: str) -> bool:
        """Mock bucket_exists - always returns True"""
        return True

    def make_bucket(self, bucket_name: str) -> None:
        """Mock make_bucket - no-op"""
        pass


class MockQdrantClient:
    """Mock Qdrant client for testing vector search operations"""

    def __init__(self):
        self.vectors: Dict[str, Dict[str, Any]] = {}
        self.collections: Dict[str, Dict[str, Any]] = {}

    def recreate_collection(
        self,
        collection_name: str,
        vectors_config: Dict[str, Any],
    ) -> None:
        """Mock recreate_collection - creates collection in memory"""
        self.collections[collection_name] = {
            "name": collection_name,
            "vectors_config": vectors_config,
            "points": {},
        }

    def upsert(
        self,
        collection_name: str,
        points: List[Dict[str, Any]],
    ) -> None:
        """Mock upsert - stores vectors in memory"""
        if collection_name not in self.collections:
            self.collections[collection_name] = {"points": {}}

        for point in points:
            point_id = point.get("id")
            self.collections[collection_name]["points"][point_id] = point

    def search(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        query_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Mock search - returns mock search results"""
        if collection_name not in self.collections:
            return []

        # Return mock results (in real implementation, would do similarity search)
        results = []
        for point_id, point in list(self.collections[collection_name]["points"].items())[:limit]:
            results.append(
                {
                    "id": point_id,
                    "score": 0.95,
                    "payload": point.get("payload", {}),
                }
            )
        return results

    def delete(
        self,
        collection_name: str,
        points_selector: Dict[str, Any],
    ) -> None:
        """Mock delete - removes vectors from memory"""
        if collection_name in self.collections:
            point_ids = points_selector.get("points", {}).get("ids", [])
            for point_id in point_ids:
                if point_id in self.collections[collection_name]["points"]:
                    del self.collections[collection_name]["points"][point_id]

    def collection_exists(self, collection_name: str) -> bool:
        """Mock collection_exists - checks if collection exists"""
        return collection_name in self.collections


class MockRedisClient:
    """Mock Redis client for testing caching operations"""

    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.ttl: Dict[str, int] = {}

    def get(self, key: str) -> Optional[Any]:
        """Mock get - retrieves value from cache"""
        return self.cache.get(key)

    def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
    ) -> bool:
        """Mock set - stores value in cache"""
        self.cache[key] = value
        if ex:
            self.ttl[key] = ex
        return True

    def delete(self, *keys: str) -> int:
        """Mock delete - removes keys from cache"""
        count = 0
        for key in keys:
            if key in self.cache:
                del self.cache[key]
                count += 1
            if key in self.ttl:
                del self.ttl[key]
        return count

    def exists(self, *keys: str) -> int:
        """Mock exists - checks if keys exist"""
        return sum(1 for key in keys if key in self.cache)

    def incr(self, key: str) -> int:
        """Mock incr - increments value"""
        current = self.cache.get(key, 0)
        new_value = current + 1
        self.cache[key] = new_value
        return new_value

    def decr(self, key: str) -> int:
        """Mock decr - decrements value"""
        current = self.cache.get(key, 0)
        new_value = current - 1
        self.cache[key] = new_value
        return new_value

    def lpush(self, key: str, *values: Any) -> int:
        """Mock lpush - pushes values to list"""
        if key not in self.cache:
            self.cache[key] = []
        for value in values:
            self.cache[key].insert(0, value)
        return len(self.cache[key])

    def rpush(self, key: str, *values: Any) -> int:
        """Mock rpush - appends values to list"""
        if key not in self.cache:
            self.cache[key] = []
        for value in values:
            self.cache[key].append(value)
        return len(self.cache[key])

    def lpop(self, key: str) -> Optional[Any]:
        """Mock lpop - pops from left of list"""
        if key in self.cache and isinstance(self.cache[key], list) and self.cache[key]:
            return self.cache[key].pop(0)
        return None

    def rpop(self, key: str) -> Optional[Any]:
        """Mock rpop - pops from right of list"""
        if key in self.cache and isinstance(self.cache[key], list) and self.cache[key]:
            return self.cache[key].pop()
        return None

    def lrange(self, key: str, start: int, end: int) -> List[Any]:
        """Mock lrange - gets range from list"""
        if key in self.cache and isinstance(self.cache[key], list):
            # Handle negative indices properly
            if end == -1:
                return self.cache[key][start:]
            else:
                return self.cache[key][start : end + 1]
        return []

    def hset(self, key: str, mapping: Dict[str, Any]) -> int:
        """Mock hset - sets hash fields"""
        if key not in self.cache:
            self.cache[key] = {}
        count = 0
        for field, value in mapping.items():
            if field not in self.cache[key]:
                count += 1
            self.cache[key][field] = value
        return count

    def hget(self, key: str, field: str) -> Optional[Any]:
        """Mock hget - gets hash field"""
        if key in self.cache and isinstance(self.cache[key], dict):
            return self.cache[key].get(field)
        return None

    def hgetall(self, key: str) -> Dict[str, Any]:
        """Mock hgetall - gets all hash fields"""
        if key in self.cache and isinstance(self.cache[key], dict):
            return self.cache[key]
        return {}

    def hdel(self, key: str, *fields: str) -> int:
        """Mock hdel - deletes hash fields"""
        if key not in self.cache or not isinstance(self.cache[key], dict):
            return 0
        count = 0
        for field in fields:
            if field in self.cache[key]:
                del self.cache[key][field]
                count += 1
        return count

    def clear(self) -> None:
        """Mock clear - clears all cache"""
        self.cache.clear()
        self.ttl.clear()


def create_mock_minio_client() -> MockMinIOClient:
    """Factory function to create mock MinIO client"""
    return MockMinIOClient()


def create_mock_qdrant_client() -> MockQdrantClient:
    """Factory function to create mock Qdrant client"""
    return MockQdrantClient()


def create_mock_redis_client() -> MockRedisClient:
    """Factory function to create mock Redis client"""
    return MockRedisClient()
