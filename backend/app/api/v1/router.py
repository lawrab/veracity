"""
Main API router for v1 endpoints.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ingestion,
    pipeline,
    processing,
    sources,
    stories,
    trends,
    trust,
    websocket_enhanced,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(trends.router, prefix="/trends", tags=["trends"])
api_router.include_router(stories.router, prefix="/stories", tags=["stories"])
api_router.include_router(sources.router, prefix="/sources", tags=["sources"])
api_router.include_router(ingestion.router, prefix="/ingestion", tags=["ingestion"])
api_router.include_router(processing.router, prefix="/processing", tags=["processing"])
api_router.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
api_router.include_router(websocket_enhanced.router, prefix="/ws", tags=["websocket"])
api_router.include_router(trust.router, prefix="/trust", tags=["trust-scoring"])
