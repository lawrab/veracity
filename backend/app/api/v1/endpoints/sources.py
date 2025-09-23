"""
Sources API endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_postgres_session
from app.schemas.source import SourceResponse
from app.services.source_service import SourceService

router = APIRouter()


@router.get("/", response_model=List[SourceResponse])
async def get_sources(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    platform: Optional[str] = Query(None),
    verified_only: bool = Query(False),
    db: AsyncSession = Depends(get_postgres_session),
):
    """
    Get sources with optional filtering.

    - **skip**: Number of sources to skip
    - **limit**: Maximum number of sources to return
    - **platform**: Filter by platform type
    - **verified_only**: Show only verified sources
    """
    source_service = SourceService(db)
    return await source_service.get_sources(
        skip=skip, limit=limit, platform=platform, verified_only=verified_only
    )


@router.get("/{source_id}", response_model=SourceResponse)
async def get_source(
    source_id: str,
    db: AsyncSession = Depends(get_postgres_session),
):
    """Get specific source by ID."""
    source_service = SourceService(db)
    source = await source_service.get_source_by_id(source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.get("/{source_id}/credibility-history")
async def get_source_credibility_history(
    source_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_postgres_session),
):
    """Get credibility score history for a source."""
    source_service = SourceService(db)
    history = await source_service.get_credibility_history(source_id, days)
    if history is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return history


@router.get("/stats/platform-breakdown")
async def get_platform_stats(
    db: AsyncSession = Depends(get_postgres_session),
):
    """Get statistics breakdown by platform."""
    source_service = SourceService(db)
    return await source_service.get_platform_stats()
