"""
Trends API endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_postgres_session
from app.schemas.trend import TrendCreate, TrendResponse
from app.services.trend_service import TrendService

router = APIRouter()


@router.get("/", response_model=List[TrendResponse])
async def get_trends(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    platform: Optional[str] = Query(None),
    time_window: Optional[str] = Query("1h"),
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


@router.get("/{trend_id}", response_model=TrendResponse)
async def get_trend(
    trend_id: str,
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
    trend_id: str,
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
    trend_id: str,
    db: AsyncSession = Depends(get_postgres_session),
):
    """Get sources contributing to a trend."""
    trend_service = TrendService(db)
    sources = await trend_service.get_trend_sources(trend_id)
    if sources is None:
        raise HTTPException(status_code=404, detail="Trend not found")
    return sources
