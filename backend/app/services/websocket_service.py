"""
WebSocket service for real-time communications.
"""

import asyncio
import json
from typing import Dict, Set

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """Manages WebSocket connections and broadcasting."""

    def __init__(self):
        # Channel -> Set of connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        """Accept a WebSocket connection and add to channel."""
        await websocket.accept()

        if channel not in self.active_connections:
            self.active_connections[channel] = set()

        self.active_connections[channel].add(websocket)
        logger.info(
            f"Client connected to channel '{channel}'. Total: {len(self.active_connections[channel])}"
        )

    def disconnect(self, websocket: WebSocket, channel: str):
        """Remove a WebSocket connection from channel."""
        if channel in self.active_connections:
            self.active_connections[channel].discard(websocket)
            if not self.active_connections[channel]:
                del self.active_connections[channel]

        logger.info(f"Client disconnected from channel '{channel}'")

    async def send_message_to_connection(self, websocket: WebSocket, message: dict):
        """Send message to a specific connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message to connection: {e}")

    async def broadcast_to_channel(self, channel: str, message: dict):
        """Broadcast message to all connections in a channel."""
        if channel not in self.active_connections:
            return

        message_text = json.dumps(message)
        disconnected = set()

        for websocket in self.active_connections[channel]:
            try:
                await websocket.send_text(message_text)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.add(websocket)

        # Remove disconnected connections
        for websocket in disconnected:
            self.disconnect(websocket, channel)

    async def broadcast_trend_update(self, trend_data: dict):
        """Broadcast trend update to all trend subscribers."""
        await self.broadcast_to_channel(
            "trends",
            {
                "type": "trend_update",
                "data": trend_data,
                "timestamp": trend_data.get("created_at"),
            },
        )

    async def broadcast_trust_score_update(
        self, story_id: str, trust_score: float, signals: list
    ):
        """Broadcast trust score update."""
        message = {
            "type": "trust_score_update",
            "story_id": story_id,
            "trust_score": trust_score,
            "signals": signals,
            "timestamp": asyncio.get_event_loop().time(),
        }

        # Broadcast to general trust score channel
        await self.broadcast_to_channel("trust_scores", message)

        # Broadcast to specific story channel
        await self.broadcast_to_channel(f"story_{story_id}", message)

    async def broadcast_story_update(self, story_data: dict):
        """Broadcast story update to relevant channels."""
        story_id = story_data.get("id")

        message = {
            "type": "story_update",
            "data": story_data,
            "timestamp": story_data.get("last_updated_at"),
        }

        if story_id:
            await self.broadcast_to_channel(f"story_{story_id}", message)

    def get_channel_stats(self) -> Dict[str, int]:
        """Get statistics about active connections."""
        return {
            channel: len(connections)
            for channel, connections in self.active_connections.items()
        }


# Global WebSocket manager instance
websocket_manager = WebSocketManager()
