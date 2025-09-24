"""
Trends API endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import get_postgres_session
from app.schemas.trend import TrendResponse
from app.services.trend_service import TrendService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.get("/", response_model=list[TrendResponse])
async def get_trends(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    platform: str | None = Query(None),
    time_window: str | None = Query("1h"),
    db: AsyncSession = Depends(get_postgres_session),
):
    """
    Get trending topics with optional filtering.

    - **skip**: Number of trends to skip
    - **limit**: Maximum number of trends to return
    - **platform**: Filter by platform (twitter, reddit, etc.)
    - **time_window**: Time window for trends (1h, 6h, 24h)
    """
    trend_service = TrendService(db)
    return await trend_service.get_trending(
        skip=skip, limit=limit, platform=platform, time_window=time_window
    )

@router.get("/live", response_model=list[TrendResponse])
async def get_live_trends(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_postgres_session),
):
    """
    Get live/real-time trends ordered by recent activity.
    
    - **limit**: Maximum number of live trends to return
    """
    trend_service = TrendService(db)
    return await trend_service.get_live_trends(limit=limit)


@router.get("/{trend_id}", response_model=TrendResponse)
async def get_trend(
    trend_id: UUID,
    db: AsyncSession = Depends(get_postgres_session),
):
    """Get specific trend by ID."""
    trend_service = TrendService(db)
    trend = await trend_service.get_trend_by_id(trend_id)
    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")
    return trend


@router.get("/{trend_id}/evolution")
async def get_trend_evolution(
    trend_id: UUID,
    db: AsyncSession = Depends(get_postgres_session),
):
    """Get trend evolution data over time."""
    trend_service = TrendService(db)
    evolution = await trend_service.get_trend_evolution(trend_id)
    if not evolution:
        raise HTTPException(status_code=404, detail="Trend not found")
    return evolution


@router.get("/{trend_id}/sources")
async def get_trend_sources(
    trend_id: UUID,
    db: AsyncSession = Depends(get_postgres_session),
):
    """Get sources contributing to a trend."""
    trend_service = TrendService(db)
    sources = await trend_service.get_trend_sources(trend_id)
    if sources is None:
        raise HTTPException(status_code=404, detail="Trend not found")
    return sources
