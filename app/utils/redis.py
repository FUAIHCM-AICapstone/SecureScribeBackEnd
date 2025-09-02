import redis
from redis import ConnectionPool

from app.core.config import settings

# Create connection pool for better performance
redis_pool = ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,
    max_connections=20,
    retry_on_timeout=True,
    socket_timeout=5,
    socket_connect_timeout=5,
    socket_keepalive=True,
    socket_keepalive_options={},
    health_check_interval=30,
)

redis_client = redis.Redis(connection_pool=redis_pool)


def get_redis_client():
    """
    Get Redis client with error handling
    """
    try:
        return redis_client
    except Exception as e:
        print(f"Redis connection error: {e}")
        # Fallback to new connection if pool fails
        return redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
        )


def test_redis_connection():
    """
    Test Redis connection
    """
    try:
        redis_client.ping()
        return True
    except Exception as e:
        print(f"Redis connection test failed: {e}")
        return False
