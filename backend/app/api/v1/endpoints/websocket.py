"""
WebSocket endpoints for real-time updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.services.websocket_service import WebSocketManager

router = APIRouter()
websocket_manager = WebSocketManager()
logger = get_logger(__name__)


@router.websocket("/trends")
async def websocket_trends(websocket: WebSocket):
    """WebSocket endpoint for real-time trend updates."""
    await websocket_manager.connect(websocket, "trends")
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            # Echo back for now (can be extended for client commands)
            await websocket_manager.send_message_to_connection(
                websocket, {"type": "ping", "data": data}
            )
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "trends")
        logger.info("Client disconnected from trends feed")


@router.websocket("/stories/{story_id}")
async def websocket_story_updates(websocket: WebSocket, story_id: str):
    """WebSocket endpoint for specific story updates."""
    channel = f"story_{story_id}"
    await websocket_manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket_manager.send_message_to_connection(
                websocket, {"type": "story_update", "story_id": story_id, "data": data}
            )
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, channel)
        logger.info(f"Client disconnected from story {story_id} updates")


@router.websocket("/trust-scores")
async def websocket_trust_scores(websocket: WebSocket):
    """WebSocket endpoint for trust score updates."""
    await websocket_manager.connect(websocket, "trust_scores")
    try:
        while True:
            data = await websocket.receive_text()
            await websocket_manager.send_message_to_connection(
                websocket, {"type": "trust_score_update", "data": data}
            )
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, "trust_scores")
        logger.info("Client disconnected from trust score updates")
