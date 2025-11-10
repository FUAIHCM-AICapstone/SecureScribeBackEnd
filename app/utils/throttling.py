import asyncio
import logging
import time
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.utils.redis import get_async_redis_client

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Redis-based sliding window rate limiter using sorted sets.
    Tracks request timestamps and automatically cleans up old entries.
    """

    def __init__(
        self,
        window_seconds: int = settings.THROTTLING_WINDOW_SECONDS,
        max_requests: int = settings.THROTTLING_MAX_REQUESTS_API,
        redis_key_prefix: str = settings.THROTTLING_REDIS_KEY_PREFIX,
    ):
        self.window_seconds = window_seconds
        self.max_requests = max_requests
        self.redis_key_prefix = redis_key_prefix

    def _get_key(self, identifier: str) -> str:
        """Generate Redis key for the identifier."""
        return f"{self.redis_key_prefix}:{identifier}"

    async def is_allowed(self, identifier: str) -> Tuple[bool, int, float]:
        """
        Check if request is allowed for the given identifier.

        Returns:
            Tuple of (is_allowed, remaining_requests, reset_time_seconds)
        """
        try:
            client = await get_async_redis_client()
            key = self._get_key(identifier)
            current_time = time.time()

            # Remove old entries outside the sliding window
            min_score = current_time - self.window_seconds
            await client.zremrangebyscore(key, '-inf', min_score)

            # Count current requests in the window
            request_count = await client.zcard(key)

            if request_count >= self.max_requests:
                # Get the oldest timestamp to calculate reset time
                oldest_timestamps = await client.zrange(key, 0, 0, withscores=True)
                if oldest_timestamps:
                    oldest_time = oldest_timestamps[0][1]
                    reset_time = oldest_time + self.window_seconds - current_time
                else:
                    reset_time = self.window_seconds

                remaining = 0
                return False, remaining, max(0, reset_time)

            # Add current request timestamp
            await client.zadd(key, {str(current_time): current_time})

            # Set expiration on the key (cleanup old data)
            await client.expire(key, self.window_seconds * 2)

            remaining = self.max_requests - request_count - 1
            reset_time = self.window_seconds

            return True, remaining, reset_time

        except Exception as e:
            # Fail open - allow request if Redis is unavailable
            logger.warning("Rate limiter Redis error: %s. Allowing request.", e)
            return True, self.max_requests - 1, self.window_seconds

    async def cleanup_old_entries(self):
        """Background task to clean up old rate limit entries."""
        try:
            client = await get_async_redis_client()
            current_time = time.time()
            min_score = current_time - (self.window_seconds * 2)  # Keep 2x window for safety

            # Find all rate limit keys
            keys = await client.keys(f"{self.redis_key_prefix}:*")

            for key in keys:
                # Remove entries older than 2x window
                await client.zremrangebyscore(key, '-inf', min_score)

                # If key is empty, it will expire naturally due to TTL
        except Exception as e:
            logger.error("Failed to cleanup rate limit entries: %s", e)


class ThrottlingMiddleware:
    """
    FastAPI middleware for rate limiting based on client IP address.
    Different limits for different endpoint types.
    """

    def __init__(self, app):
        self.app = app
        self.rate_limiters = {
            'health': RateLimiter(
                max_requests=settings.THROTTLING_MAX_REQUESTS_HEALTH,
                window_seconds=settings.THROTTLING_WINDOW_SECONDS,
            ),
            'upload': RateLimiter(
                max_requests=settings.THROTTLING_MAX_REQUESTS_UPLOAD,
                window_seconds=settings.THROTTLING_WINDOW_SECONDS,
            ),
            'api': RateLimiter(
                max_requests=settings.THROTTLING_MAX_REQUESTS_API,
                window_seconds=settings.THROTTLING_WINDOW_SECONDS,
            ),
        }

        # Start background cleanup task
        if settings.THROTTLING_ENABLED:
            asyncio.create_task(self._periodic_cleanup())

    async def _periodic_cleanup(self):
        """Run periodic cleanup of old rate limit entries."""
        while True:
            try:
                for limiter in self.rate_limiters.values():
                    await limiter.cleanup_old_entries()
                await asyncio.sleep(settings.THROTTLING_CLEANUP_INTERVAL)
            except Exception as e:
                logger.error("Rate limit cleanup task error: %s", e)
                await asyncio.sleep(60)  # Retry in 1 minute on error

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request headers."""
        # Check for forwarded headers (common in proxy setups)
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            # Take the first IP if there are multiple
            return forwarded_for.split(',')[0].strip()

        # Check for other proxy headers
        real_ip = request.headers.get('x-real-ip')
        if real_ip:
            return real_ip.strip()

        # Fallback to direct client IP
        return request.client.host if request.client else 'unknown'

    def _get_client_ip_from_scope(self, scope) -> str:
        """Extract client IP address from ASGI scope."""
        headers = dict(scope.get('headers', []))

        # Check for forwarded headers (common in proxy setups)
        forwarded_for = headers.get(b'x-forwarded-for')
        if forwarded_for:
            # Decode and take the first IP if there are multiple
            forwarded_str = forwarded_for.decode('utf-8', errors='ignore')
            return forwarded_str.split(',')[0].strip()

        # Check for other proxy headers
        real_ip = headers.get(b'x-real-ip')
        if real_ip:
            return real_ip.decode('utf-8', errors='ignore').strip()

        # Fallback to direct client IP from scope
        client = scope.get('client')
        if client and len(client) >= 1:
            return client[0]
        return 'unknown'

    def _get_endpoint_type(self, path: str) -> str:
        """Determine endpoint type based on path."""
        if path.startswith('/be/health'):
            return 'health'
        elif any(path.startswith(prefix) for prefix in ['/be/api/v1/files', '/be/api/v1/audio']):
            return 'upload'
        else:
            return 'api'

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # Pass through non-HTTP requests (like websockets)
            return await self.app(scope, receive, send)

        if not settings.THROTTLING_ENABLED:
            return await self.app(scope, receive, send)

        # Skip throttling for certain paths (like static files, WebSocket endpoints, etc.)
        path = scope.get("path", "")
        headers = dict(scope.get('headers', []))

        # Skip throttling for WebSocket handshake requests (Upgrade: websocket header)
        upgrade_header = headers.get(b'upgrade', b'').decode('utf-8', errors='ignore').lower()
        if path in ['/be/search-test', '/be/test-auth'] or path.endswith('/ws') or upgrade_header == 'websocket':
            return await self.app(scope, receive, send)

        # Extract client IP from ASGI scope
        client_ip = self._get_client_ip_from_scope(scope)
        endpoint_type = self._get_endpoint_type(path)
        limiter = self.rate_limiters[endpoint_type]

        # Check rate limit
        is_allowed, remaining, reset_time = await limiter.is_allowed(client_ip)

        if not is_allowed:
            logger.warning(
                "Rate limit exceeded for IP %s on %s endpoint. Remaining: %d, Reset in: %.1fs",
                client_ip, endpoint_type, remaining, reset_time
            )

            # Send rate limit exceeded response
            response_body = {
                "error": "Too Many Requests",
                "message": "Rate limit exceeded. Please try again later.",
                "retry_after": int(reset_time),
                "limit": limiter.max_requests,
                "window_seconds": limiter.window_seconds,
            }
            import json
            response_bytes = json.dumps(response_body).encode('utf-8')

            await send({
                'type': 'http.response.start',
                'status': 429,
                'headers': [
                    [b'content-type', b'application/json'],
                    [b'retry-after', str(int(reset_time)).encode()],
                    [b'x-ratelimit-limit', str(limiter.max_requests).encode()],
                    [b'x-ratelimit-remaining', str(remaining).encode()],
                    [b'x-ratelimit-reset', str(int(time.time() + reset_time)).encode()],
                ],
            })
            await send({
                'type': 'http.response.body',
                'body': response_bytes,
            })
            return

        # Wrap the send function to add rate limit headers
        original_send = send

        async def send_with_headers(message):
            if message['type'] == 'http.response.start':
                headers = list(message.get('headers', []))
                headers.extend([
                    [b'x-ratelimit-limit', str(limiter.max_requests).encode()],
                    [b'x-ratelimit-remaining', str(remaining).encode()],
                    [b'x-ratelimit-reset', str(int(time.time() + reset_time)).encode()],
                ])
                message['headers'] = headers
            await original_send(message)

        return await self.app(scope, receive, send_with_headers)
