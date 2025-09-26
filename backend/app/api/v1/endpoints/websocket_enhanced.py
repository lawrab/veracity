"""
Enhanced WebSocket endpoints with authentication, heartbeat, and scaling.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Header
from typing import Optional

from app.core.logging import get_logger
from app.services.websocket_manager import websocket_manager

router = APIRouter()
logger = get_logger(__name__)


@router.on_event("startup")
async def startup_event():
    """Initialize WebSocket manager on startup."""
    await websocket_manager.initialize()
    logger.info("WebSocket manager initialized")


@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup WebSocket manager on shutdown."""
    await websocket_manager.cleanup()
    logger.info("WebSocket manager cleanup complete")


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: Optional[str] = Query(default="general"),
    token: Optional[str] = Header(default=None)
):
    """
    Main WebSocket endpoint with multi-channel support.
    
    Clients can:
    - Connect with optional authentication token
    - Subscribe/unsubscribe to multiple channels
    - Receive real-time updates
    - Send heartbeat responses
    """
    # Extract user_id from token if available
    user_id = None
    if token:
        # TODO: Decode JWT token to get user_id
        user_id = f"user_{token[:8]}"  # Placeholder
    
    # Connect to WebSocket
    connected = await websocket_manager.connect(
        websocket=websocket,
        channel=channel,
        user_id=user_id,
        auth_token=token
    )
    
    if not connected:
        return
    
    try:
        while True:
            # Handle incoming messages
            message = await websocket.receive_text()
            await websocket_manager.handle_message(websocket, message)
            
    except WebSocketDisconnect:
        await websocket_manager.disconnect(websocket)
        logger.info(f"Client disconnected from {channel}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket_manager.disconnect(websocket)


@router.websocket("/trends")
async def websocket_trends(
    websocket: WebSocket,
    token: Optional[str] = Header(default=None)
):
    """WebSocket endpoint specifically for trend updates."""
    await websocket_endpoint(websocket, "trends", token)


@router.websocket("/stories")
async def websocket_stories(
    websocket: WebSocket,
    token: Optional[str] = Header(default=None)
):
    """WebSocket endpoint for story updates."""
    await websocket_endpoint(websocket, "stories", token)


@router.websocket("/stories/{story_id}")
async def websocket_story_specific(
    websocket: WebSocket,
    story_id: str,
    token: Optional[str] = Header(default=None)
):
    """WebSocket endpoint for specific story updates."""
    await websocket_endpoint(websocket, f"story:{story_id}", token)


@router.websocket("/trust-scores")
async def websocket_trust_scores(
    websocket: WebSocket,
    token: Optional[str] = Header(default=None)
):
    """WebSocket endpoint for trust score updates."""
    await websocket_endpoint(websocket, "trust_scores", token)


@router.get("/stats")
async def websocket_stats():
    """Get WebSocket connection statistics."""
    return websocket_manager.get_stats()