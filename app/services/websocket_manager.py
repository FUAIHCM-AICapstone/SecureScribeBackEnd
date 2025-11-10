import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Set

from fastapi import WebSocket

from app.utils.redis import (
    get_async_redis_client,
    get_recent_messages_for_user,
    publish_to_user_channel,
)

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """
    Enhanced WebSocket manager with Redis pub/sub integration.
    Supports hierarchical channels, message replay, and connection management.
    """

    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}  # user_id -> set of WebSocket connections
        self._redis_client = None
        self._pubsub_task: Optional[asyncio.Task] = None
        self._stop = False
        self._metrics = {
            "total_connections": 0,
            "active_connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "redis_errors": 0,
            "websocket_errors": 0,
        }

    def add_connection(self, user_id: str, websocket: WebSocket) -> None:
        """Add a WebSocket connection for a user."""
        if user_id not in self.connections:
            self.connections[user_id] = set()

        self.connections[user_id].add(websocket)
        self._metrics["total_connections"] += 1
        self._metrics["active_connections"] = sum(len(conns) for conns in self.connections.values())

        logger.info(
            "Added WebSocket connection for user %s (total users: %s, active connections: %s)",
            user_id,
            len(self.connections),
            self._metrics["active_connections"],
        )

    def remove_connection(self, user_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection for a user."""
        if user_id in self.connections:
            self.connections[user_id].discard(websocket)

            if not self.connections[user_id]:
                del self.connections[user_id]

            self._metrics["active_connections"] = sum(len(conns) for conns in self.connections.values())
            logger.info(
                "Removed WebSocket connection for user %s (remaining connections: %s)",
                user_id,
                self._metrics["active_connections"],
            )

    async def broadcast_to_user(self, user_id: str, message_data: dict) -> int:
        """
        Broadcast message to all WebSocket connections for a user.
        Returns the number of connections that received the message.
        """
        if user_id not in self.connections:
            return 0

        connections = list(self.connections[user_id])
        if not connections:
            return 0

        sent_count = 0
        failed_connections = []

        for websocket in connections:
            try:
                await websocket.send_json(message_data)
                sent_count += 1
                self._metrics["messages_sent"] += 1
            except RuntimeError as e:
                # Handle closed WebSocket connections specifically
                if "close message has been sent" in str(e):
                    logger.debug("WebSocket connection for user %s is already closed, removing from connections", user_id)
                    failed_connections.append(websocket)
                else:
                    logger.exception("RuntimeError sending message to user %s: %s", user_id, e)
                    failed_connections.append(websocket)
                    self._metrics["websocket_errors"] += 1
            except Exception as e:
                logger.exception("Failed to send message to user %s: %s", user_id, e)
                failed_connections.append(websocket)
                self._metrics["websocket_errors"] += 1

        # Clean up failed connections
        for websocket in failed_connections:
            self.remove_connection(user_id, websocket)

        if sent_count > 0:
            logger.debug(
                "Sent message to %s/%s connections for user %s",
                sent_count,
                len(connections),
                user_id,
            )

        return sent_count

    async def handle_redis_message(self, channel: str, message_data: str) -> None:
        """Handle incoming Redis pub/sub message."""
        try:
            # Parse hierarchical channel: user:{user_id}:{message_type}
            if not channel.startswith("user:"):
                return

            parts = channel.split(":")
            if len(parts) < 3:
                logger.warning("Invalid channel format: %s", channel)
                return

            user_id = parts[1]
            message_type = parts[2]

            # Parse message data
            try:
                message = json.loads(message_data)
            except json.JSONDecodeError as e:
                logger.exception("Invalid JSON in Redis message: %s", e)
                return

            # Add metadata
            message["received_at"] = datetime.utcnow().isoformat() + "Z"
            message["channel"] = channel

            self._metrics["messages_received"] += 1

            # Broadcast to user's WebSocket connections
            sent_count = await self.broadcast_to_user(user_id, message)

            logger.debug(
                "Processed Redis message for user %s (type: %s, sent to %s connections)",
                user_id,
                message_type,
                sent_count,
            )

        except Exception as e:
            logger.exception("Error handling Redis message: %s", e)
            self._metrics["redis_errors"] += 1

    async def start_redis_listener(self) -> None:
        """Start the Redis pub/sub listener for user channels."""
        if self._pubsub_task and not self._pubsub_task.done():
            logger.info("Redis listener already running")
            return

        self._stop = False
        self._pubsub_task = asyncio.create_task(self._run_pubsub())
        logger.info("Started Redis pub/sub listener for user channels")

    async def stop_redis_listener(self) -> None:
        """Stop the Redis pub/sub listener."""
        self._stop = True
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass

        if self._redis_client:
            await self._redis_client.close()

        logger.info("Stopped Redis pub/sub listener")

    async def _run_pubsub(self) -> None:
        """Run the Redis pub/sub listener with exponential backoff."""
        backoff = 0.5
        max_backoff = 30.0

        while not self._stop:
            try:
                self._redis_client = await get_async_redis_client()
                pubsub = self._redis_client.pubsub()

                # Subscribe to hierarchical user channels: user:*:*
                await pubsub.psubscribe("user:*:*")
                logger.info("Subscribed to user:*:* pattern")

                while not self._stop:
                    try:
                        message = await asyncio.wait_for(
                            pubsub.get_message(ignore_subscribe_messages=True),
                            timeout=1.0,
                        )

                        if message is None:
                            continue

                        # Handle the message
                        channel = message.get("channel", "")
                        data = message.get("data", "")

                        if isinstance(data, bytes):
                            data = data.decode("utf-8")

                        await self.handle_redis_message(channel, data)

                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.exception("Error processing Redis message: %s", e)
                        break

                # Clean up subscription
                await pubsub.punsubscribe("user:*:*")
                await self._redis_client.close()

            except Exception as e:
                logger.exception("Redis pub/sub listener error: %s", e)
                self._metrics["redis_errors"] += 1

                if not self._stop:
                    logger.info("Retrying Redis connection in %.1f seconds", backoff)
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 1.5, max_backoff)
                else:
                    break

    async def replay_recent_messages(self, user_id: str, websocket: WebSocket) -> None:
        """Replay recent messages for a reconnecting client."""
        try:
            recent_messages = await get_recent_messages_for_user(user_id, limit=10)

            if recent_messages:
                logger.info(
                    "Replaying %s recent messages for user %s",
                    len(recent_messages),
                    user_id,
                )

                for message in recent_messages:
                    try:
                        await websocket.send_json(message)
                    except RuntimeError as e:
                        # Handle closed WebSocket connections specifically
                        if "close message has been sent" in str(e):
                            logger.debug("WebSocket connection for user %s is already closed during replay", user_id)
                        else:
                            logger.exception("RuntimeError replaying message to user %s: %s", user_id, e)
                        break
                    except Exception as e:
                        logger.exception("Failed to replay message to user %s: %s", user_id, e)
                        break

        except Exception as e:
            logger.exception("Failed to replay messages for user %s: %s", user_id, e)

    def get_connection_stats(self) -> dict:
        """Get connection statistics."""
        return {
            **self._metrics,
            "unique_users": len(self.connections),
            "connections_per_user": {user_id: len(connections) for user_id, connections in self.connections.items()},
        }

    async def publish_user_message(self, user_id: str, message: dict) -> bool:
        """
        Publish a message to a user's Redis channel.
        This can be used by other parts of the application.
        """
        return await publish_to_user_channel(user_id, message)


# Global instance
websocket_manager = WebSocketConnectionManager()
