"""
Trend schema definitions.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel


class TrendBase(BaseModel):
    """Base trend schema."""

    keywords: list[str]
    hashtags: list[str] | None = None
    platforms: list[str]
    mention_count: int = 0
    velocity: float = 0.0
    sentiment_score: float | None = None


class TrendCreate(TrendBase):
    """Schema for creating trends."""

    story_id: UUID | None = None


class TrendUpdate(BaseModel):
    """Schema for updating trends."""

    mention_count: int | None = None
    velocity: float | None = None
    sentiment_score: float | None = None
    peak_at: datetime | None = None


class TrendResponse(TrendBase):
    """Schema for trend responses."""

    id: UUID
    story_id: UUID | None = None
    detected_at: datetime
    peak_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class TrendEvolution(BaseModel):
    """Schema for trend evolution data."""

    timestamps: list[datetime]
    mention_counts: list[int]
    velocity_values: list[float]
    sentiment_scores: list[float | None]


class TrendSource(BaseModel):
    """Schema for trend source information."""

    platform: str
    source_count: int
    mention_count: int
    avg_credibility: float
    top_sources: list[dict]
