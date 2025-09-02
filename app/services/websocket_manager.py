import asyncio
import json
import threading
import time
from typing import Any, Dict, Optional

from fastapi import WebSocket


class WebSocketConnectionManager:
    """
    Manages WebSocket connections and broadcasts events to connected users
    """

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
        self.connection_info: Dict[str, Dict[str, Any]] = {}
        self._cleanup_task = None
        self._running = True

    def add_connection(self, user_id: str, websocket: WebSocket) -> None:
        """
        Add WebSocket connection for user
        """
        self.connections[user_id] = websocket
        self.connection_info[user_id] = {
            "connected_at": time.time(),
            "last_active": time.time()
        }
        print(f"WebSocket connection added for user: {user_id}")

    def remove_connection(self, user_id: str) -> None:
        """
        Remove WebSocket connection for user
        """
        if user_id in self.connections:
            del self.connections[user_id]
            del self.connection_info[user_id]
            print(f"WebSocket connection removed for user: {user_id}")

    async def broadcast_to_user(self, user_id: str, message_data: Dict) -> bool:
        """
        Broadcast message to specific user via WebSocket
        """
        try:
            if user_id not in self.connections:
                print(f"No active WebSocket connection for user: {user_id}")
                return False

            websocket = self.connections[user_id]
            connection_info = self.connection_info[user_id]

            # Check if connection is still active (within 5 minutes)
            if time.time() - connection_info["last_active"] > 300:
                print(f"WebSocket connection for user {user_id} is stale, removing...")
                self.remove_connection(user_id)
                return False

            # Update last active time
            connection_info["last_active"] = time.time()

            # Send message via WebSocket
            try:
                await websocket.send_json(message_data)
                print(f"Successfully sent message to user {user_id}: {message_data.get('type', 'unknown')}")
                return True
            except Exception as send_error:
                print(f"Failed to send message to user {user_id}: {send_error}")
                # Remove failed connection
                self.remove_connection(user_id)
                return False

        except Exception as e:
            print(f"Error broadcasting to user {user_id}: {e}")
            # Remove failed connection
            self.remove_connection(user_id)
            return False

    async def broadcast_to_all(self, message_data: Dict) -> None:
        """
        Broadcast message to all connected users
        """
        disconnected_users = []

        for user_id in list(self.connections.keys()):
            success = await self.broadcast_to_user(user_id, message_data)
            if not success:
                disconnected_users.append(user_id)

        # Clean up disconnected users
        for user_id in disconnected_users:
            self.remove_connection(user_id)

    def get_active_connections(self) -> Dict[str, Any]:
        """
        Get information about active WebSocket connections
        """
        return {
            user_id: {
                "connected_at": info["connected_at"],
                "last_active": info["last_active"],
                "active_time": time.time() - info["connected_at"]
            }
            for user_id, info in self.connection_info.items()
        }

    def get_connection_count(self) -> int:
        """
        Get the number of active connections
        """
        return len(self.connections)

    async def cleanup_inactive_connections(self) -> None:
        """
        Remove WebSocket connections that have been inactive for more than 5 minutes
        """
        current_time = time.time()
        inactive_threshold = 300  # 5 minutes

        disconnected_users = []
        for user_id, info in self.connection_info.items():
            if current_time - info["last_active"] > inactive_threshold:
                disconnected_users.append(user_id)
                print(f"WebSocket connection for user {user_id} is inactive, will remove")

        # Close connections and remove from tracking
        for user_id in disconnected_users:
            try:
                websocket = self.connections[user_id]
                await websocket.close(code=1001, reason="Connection inactive")
            except Exception as e:
                print(f"Error closing inactive connection for user {user_id}: {e}")
            finally:
                self.remove_connection(user_id)

    async def start_cleanup_task(self) -> None:
        """
        Start background task for cleaning up inactive connections
        """
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self.cleanup_inactive_connections()
            except Exception as e:
                print(f"Error in cleanup task: {e}")

    def stop_cleanup_task(self) -> None:
        """
        Stop cleanup task
        """
        self._running = False

    async def send_ping_to_all(self) -> None:
        """
        Send ping messages to all connected clients to keep connections alive
        """
        ping_message = {"type": "ping", "timestamp": time.time()}

        disconnected_users = []
        for user_id in list(self.connections.keys()):
            try:
                await self.connections[user_id].send_json(ping_message)
                print(f"Sent ping to user {user_id}")
            except Exception as e:
                print(f"Failed to ping user {user_id}: {e}")
                disconnected_users.append(user_id)

        # Clean up failed connections
        for user_id in disconnected_users:
            self.remove_connection(user_id)


# Global WebSocket manager instance
websocket_manager = WebSocketConnectionManager()
