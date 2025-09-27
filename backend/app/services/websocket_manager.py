"""
Enhanced WebSocket Manager with Redis pub/sub for scaling.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections import defaultdict
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import WebSocket, WebSocketDisconnect, status

from app.core.config import settings
from app.core.database import get_redis_client
from app.core.logging import get_logger

if TYPE_CHECKING:
    import redis.asyncio as redis
    from fastapi import WebSocket

logger = get_logger(__name__)


class ConnectionInfo:
    """Track connection metadata."""

    def __init__(self, websocket: WebSocket, user_id: str | None = None):
        self.websocket = websocket
        self.user_id = user_id
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = datetime.utcnow()
        self.subscribed_channels: set[str] = set()
        self.message_count = 0
        self.rate_limit_window = datetime.utcnow()
        self.rate_limit_count = 0
        self.heartbeat_task: asyncio.Task | None = None


class EnhancedWebSocketManager:
    """
    Enhanced WebSocket manager with Redis pub/sub, authentication,
    heartbeat, and rate limiting.
    """

    # Rate limiting configuration
    RATE_LIMIT_MESSAGES = 100  # messages per window
    RATE_LIMIT_WINDOW = 60  # seconds

    # Heartbeat configuration
    HEARTBEAT_INTERVAL = 30  # seconds
    HEARTBEAT_TIMEOUT = 90  # seconds

    def __init__(self):
        self.connections: dict[WebSocket, ConnectionInfo] = {}
        self.channels: dict[str, set[WebSocket]] = defaultdict(set)
        self.redis_client: redis.Redis | None = None
        self.pubsub: redis.client.PubSub | None = None
        self.pubsub_task: asyncio.Task | None = None
        self._initialized = False

    async def initialize(self):
        """Initialize Redis pub/sub connection."""
        if self._initialized:
            return

        try:
            self.redis_client = get_redis_client()
            if self.redis_client:
                self.pubsub = self.redis_client.pubsub()
                await self.pubsub.subscribe("websocket:broadcast")
                self.pubsub_task = asyncio.create_task(self._redis_listener())
                self._initialized = True
                logger.info("WebSocket manager initialized with Redis pub/sub")
            else:
                logger.warning("Redis not available, WebSocket scaling disabled")
        except Exception as e:
            logger.exception(f"Failed to initialize Redis pub/sub: {e}")

    async def _redis_listener(self):
        """Listen for Redis pub/sub messages."""
        if not self.pubsub:
            return

        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        channel = data.get("channel")
                        payload = data.get("payload")

                        if channel and payload:
                            # Broadcast to local connections
                            await self._local_broadcast(channel, payload)
                    except json.JSONDecodeError:
                        logger.exception("Invalid JSON in Redis message")
                    except Exception as e:
                        logger.exception(f"Error processing Redis message: {e}")
        except asyncio.CancelledError:
            logger.info("Redis listener cancelled")
        except Exception as e:
            logger.exception(f"Redis listener error: {e}")

    async def connect(
        self,
        websocket: WebSocket,
        channel: str,
        user_id: str | None = None,
        auth_token: str | None = None,
    ) -> bool:
        """
        Accept WebSocket connection with optional authentication.
        Returns True if connection successful.
        """
        try:
            # Validate authentication if required
            if settings.REQUIRE_WEBSOCKET_AUTH and not await self._authenticate(
                auth_token
            ):
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return False

            await websocket.accept()

            # Create connection info
            conn_info = ConnectionInfo(websocket, user_id)
            conn_info.subscribed_channels.add(channel)

            self.connections[websocket] = conn_info
            self.channels[channel].add(websocket)

            # Send welcome message
            await self.send_direct(
                websocket,
                {
                    "type": "connection",
                    "status": "connected",
                    "channel": channel,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            # Start heartbeat
            conn_info.heartbeat_task = asyncio.create_task(
                self._heartbeat_handler(websocket)
            )

            logger.info(
                f"Client connected to channel '{channel}'. "
                f"Total connections: {len(self.connections)}"
            )
            return True

        except Exception as e:
            logger.exception(f"Connection failed: {e}")
            return False

    async def _authenticate(self, auth_token: str | None) -> bool:
        """Validate authentication token."""
        if not auth_token:
            return False

        # TODO: Implement actual token validation
        # For now, accept any non-empty token
        return bool(auth_token)

    async def _heartbeat_handler(self, websocket: WebSocket):
        """Send periodic heartbeat to detect disconnected clients."""
        while websocket in self.connections:
            try:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)

                conn_info = self.connections.get(websocket)
                if not conn_info:
                    break

                # Check if connection timed out
                if (
                    datetime.utcnow() - conn_info.last_heartbeat
                ).seconds > self.HEARTBEAT_TIMEOUT:
                    logger.warning("Connection timed out, disconnecting")
                    await self.disconnect(websocket)
                    break

                # Send heartbeat ping
                await self.send_direct(
                    websocket,
                    {"type": "ping", "timestamp": datetime.utcnow().isoformat()},
                )

            except WebSocketDisconnect:
                await self.disconnect(websocket)
                break
            except Exception as e:
                logger.exception(f"Heartbeat error: {e}")
                await self.disconnect(websocket)
                break

    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection."""
        conn_info = self.connections.get(websocket)
        if not conn_info:
            return

        # Remove from all channels
        for channel in conn_info.subscribed_channels:
            self.channels[channel].discard(websocket)
            if not self.channels[channel]:
                del self.channels[channel]

        # Cancel heartbeat task
        if conn_info.heartbeat_task and not conn_info.heartbeat_task.done():
            conn_info.heartbeat_task.cancel()

        # Remove connection info
        del self.connections[websocket]

        with contextlib.suppress(Exception):
            await websocket.close()

        logger.info(
            f"Client disconnected. Remaining connections: {len(self.connections)}"
        )

    async def handle_message(self, websocket: WebSocket, message: str):
        """
        Handle incoming WebSocket message with rate limiting.
        """
        conn_info = self.connections.get(websocket)
        if not conn_info:
            return

        # Rate limiting check
        if not self._check_rate_limit(conn_info):
            await self.send_direct(
                websocket,
                {
                    "type": "error",
                    "message": "Rate limit exceeded",
                    "retry_after": self.RATE_LIMIT_WINDOW,
                },
            )
            return

        try:
            data = json.loads(message)
            message_type = data.get("type")

            if message_type == "pong":
                # Update heartbeat timestamp
                conn_info.last_heartbeat = datetime.utcnow()

            elif message_type == "subscribe":
                # Subscribe to additional channel
                channel = data.get("channel")
                if channel:
                    await self.subscribe_to_channel(websocket, channel)

            elif message_type == "unsubscribe":
                # Unsubscribe from channel
                channel = data.get("channel")
                if channel:
                    await self.unsubscribe_from_channel(websocket, channel)

            else:
                # Echo back for now
                await self.send_direct(
                    websocket,
                    {
                        "type": "echo",
                        "data": data,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

        except json.JSONDecodeError:
            await self.send_direct(
                websocket, {"type": "error", "message": "Invalid JSON"}
            )
        except Exception as e:
            logger.exception(f"Message handling error: {e}")

    def _check_rate_limit(self, conn_info: ConnectionInfo) -> bool:
        """Check if connection exceeded rate limit."""
        now = datetime.utcnow()
        window_elapsed = (now - conn_info.rate_limit_window).seconds

        if window_elapsed >= self.RATE_LIMIT_WINDOW:
            # Reset window
            conn_info.rate_limit_window = now
            conn_info.rate_limit_count = 1
            return True

        conn_info.rate_limit_count += 1
        return conn_info.rate_limit_count <= self.RATE_LIMIT_MESSAGES

    async def subscribe_to_channel(self, websocket: WebSocket, channel: str):
        """Subscribe connection to additional channel."""
        conn_info = self.connections.get(websocket)
        if not conn_info:
            return

        if channel not in conn_info.subscribed_channels:
            conn_info.subscribed_channels.add(channel)
            self.channels[channel].add(websocket)

            await self.send_direct(
                websocket,
                {
                    "type": "subscribed",
                    "channel": channel,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    async def unsubscribe_from_channel(self, websocket: WebSocket, channel: str):
        """Unsubscribe connection from channel."""
        conn_info = self.connections.get(websocket)
        if not conn_info:
            return

        if channel in conn_info.subscribed_channels:
            conn_info.subscribed_channels.discard(channel)
            self.channels[channel].discard(websocket)

            if not self.channels[channel]:
                del self.channels[channel]

            await self.send_direct(
                websocket,
                {
                    "type": "unsubscribed",
                    "channel": channel,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    async def send_direct(self, websocket: WebSocket, message: dict):
        """Send message directly to specific connection."""
        try:
            await websocket.send_json(message)

            conn_info = self.connections.get(websocket)
            if conn_info:
                conn_info.message_count += 1

        except WebSocketDisconnect:
            await self.disconnect(websocket)
        except Exception as e:
            logger.exception(f"Failed to send message: {e}")
            await self.disconnect(websocket)

    async def broadcast(
        self, channel: str, message: dict, exclude: WebSocket | None = None
    ):
        """
        Broadcast message to channel (local and remote via Redis).
        """
        # Broadcast via Redis for other instances
        if self.redis_client and self._initialized:
            try:
                redis_message = {
                    "channel": channel,
                    "payload": message,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                await self.redis_client.publish(
                    "websocket:broadcast", json.dumps(redis_message)
                )
            except Exception as e:
                logger.exception(f"Redis publish failed: {e}")

        # Broadcast to local connections
        await self._local_broadcast(channel, message, exclude)

    async def _local_broadcast(
        self, channel: str, message: dict, exclude: WebSocket | None = None
    ):
        """Broadcast to local connections only."""
        if channel not in self.channels:
            return

        disconnected = set()

        for websocket in self.channels[channel]:
            if websocket == exclude:
                continue

            try:
                await websocket.send_json(message)

                conn_info = self.connections.get(websocket)
                if conn_info:
                    conn_info.message_count += 1

            except WebSocketDisconnect:
                disconnected.add(websocket)
            except Exception as e:
                logger.exception(f"Broadcast error: {e}")
                disconnected.add(websocket)

        # Clean up disconnected
        for websocket in disconnected:
            await self.disconnect(websocket)

    async def broadcast_trend_update(self, trend_data: dict):
        """Broadcast trend update to all subscribers."""
        message = {
            "type": "trend_update",
            "data": trend_data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        await self.broadcast("trends", message)

    async def broadcast_trust_score_update(
        self, story_id: str, trust_score: float, signals: list
    ):
        """Broadcast trust score update."""
        message = {
            "type": "trust_score_update",
            "story_id": story_id,
            "trust_score": trust_score,
            "signals": signals,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Broadcast to general channel
        await self.broadcast("trust_scores", message)

        # Broadcast to story-specific channel
        await self.broadcast(f"story:{story_id}", message)

    async def broadcast_story_update(self, story_data: dict):
        """Broadcast story update."""
        story_id = story_data.get("id")
        message = {
            "type": "story_update",
            "data": story_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Broadcast to stories channel
        await self.broadcast("stories", message)

        # Broadcast to specific story channel
        if story_id:
            await self.broadcast(f"story:{story_id}", message)

    def get_stats(self) -> dict:
        """Get WebSocket statistics."""
        return {
            "total_connections": len(self.connections),
            "channels": {
                channel: len(connections)
                for channel, connections in self.channels.items()
            },
            "users": len(
                {conn.user_id for conn in self.connections.values() if conn.user_id}
            ),
            "redis_connected": self._initialized and self.redis_client is not None,
        }

    async def cleanup(self):
        """Cleanup resources on shutdown."""
        # Cancel Redis listener
        if self.pubsub_task:
            self.pubsub_task.cancel()

        # Unsubscribe from Redis
        if self.pubsub:
            await self.pubsub.unsubscribe()
            await self.pubsub.close()

        # Disconnect all clients
        for websocket in list(self.connections.keys()):
            await self.disconnect(websocket)

        logger.info("WebSocket manager cleanup complete")


# Global enhanced WebSocket manager instance
websocket_manager = EnhancedWebSocketManager()
