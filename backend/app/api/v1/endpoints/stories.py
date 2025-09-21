"""
Stories API endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_postgres_session
from app.schemas.story import StoryResponse, StoryCreate
from app.services.story_service import StoryService

router = APIRouter()


@router.get("/", response_model=List[StoryResponse])
async def get_stories(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    trust_score_min: Optional[float] = Query(None, ge=0, le=100),
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_postgres_session),
):
    """
    Get stories with optional filtering.
    
    - **skip**: Number of stories to skip
    - **limit**: Maximum number of stories to return
    - **trust_score_min**: Minimum trust score filter
    - **category**: Filter by story category
    """
    story_service = StoryService(db)
    return await story_service.get_stories(
        skip=skip,
        limit=limit,
        trust_score_min=trust_score_min,
        category=category
    )


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(
    story_id: str,
    db: AsyncSession = Depends(get_postgres_session),
):
    """Get specific story by ID."""
    story_service = StoryService(db)
    story = await story_service.get_story_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.get("/{story_id}/trust-history")
async def get_story_trust_history(
    story_id: str,
    db: AsyncSession = Depends(get_postgres_session),
):
    """Get trust score history for a story."""
    story_service = StoryService(db)
    history = await story_service.get_trust_score_history(story_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return history


@router.get("/{story_id}/correlations")
async def get_story_correlations(
    story_id: str,
    db: AsyncSession = Depends(get_postgres_session),
):
    """Get correlations between social trends and mainstream news."""
    story_service = StoryService(db)
    correlations = await story_service.get_story_correlations(story_id)
    if correlations is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return correlations