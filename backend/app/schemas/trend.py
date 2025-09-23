"""
Trend schema definitions.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TrendBase(BaseModel):
    """Base trend schema."""

    keywords: List[str]
    hashtags: Optional[List[str]] = None
    platforms: List[str]
    mention_count: int = 0
    velocity: float = 0.0
    sentiment_score: Optional[float] = None


class TrendCreate(TrendBase):
    """Schema for creating trends."""

    story_id: Optional[UUID] = None


class TrendUpdate(BaseModel):
    """Schema for updating trends."""

    mention_count: Optional[int] = None
    velocity: Optional[float] = None
    sentiment_score: Optional[float] = None
    peak_at: Optional[datetime] = None


class TrendResponse(TrendBase):
    """Schema for trend responses."""

    id: UUID
    story_id: Optional[UUID] = None
    detected_at: datetime
    peak_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TrendEvolution(BaseModel):
    """Schema for trend evolution data."""

    timestamps: List[datetime]
    mention_counts: List[int]
    velocity_values: List[float]
    sentiment_scores: List[Optional[float]]


class TrendSource(BaseModel):
    """Schema for trend source information."""

    platform: str
    source_count: int
    mention_count: int
    avg_credibility: float
    top_sources: List[dict]
