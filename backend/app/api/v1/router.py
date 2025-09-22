"""
Main API router for v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import trends, stories, sources, websocket, ingestion

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(trends.router, prefix="/trends", tags=["trends"])
api_router.include_router(stories.router, prefix="/stories", tags=["stories"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])