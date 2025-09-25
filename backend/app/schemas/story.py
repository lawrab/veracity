"""
Story schema definitions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class StoryBase(BaseModel):
    """Base story schema."""

    title: str = Field(..., max_length=500)
    description: str | None = None
    category: str | None = None
    trust_score: float = Field(default=0.0, ge=0.0, le=100.0)
    velocity: float = Field(default=0.0, ge=0.0)
    geographic_spread: dict[str, float] | None = None


class StoryCreate(StoryBase):
    """Schema for creating stories."""

    first_seen_at: datetime


class StoryUpdate(BaseModel):
    """Schema for updating stories."""

    title: str | None = Field(None, max_length=500)
    description: str | None = None
    trust_score: float | None = Field(None, ge=0.0, le=100.0)
    velocity: float | None = Field(None, ge=0.0)
    geographic_spread: dict[str, float] | None = None


class StoryResponse(StoryBase):
    """Schema for story responses."""

    id: UUID
    first_seen_at: datetime
    last_updated_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class TrustScoreHistory(BaseModel):
    """Schema for trust score history."""

    timestamps: list[datetime]
    scores: list[float]
    signals: list[dict[str, Any]]  # Contributing factors at each point


class StoryCorrelation(BaseModel):
    """Schema for story correlations with news."""

    news_article_url: str
    news_source: str
    news_title: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    time_to_mainstream_hours: float | None = None
    found_at: datetime


class StoryCorrelationsResponse(BaseModel):
    """Schema for story correlation responses."""

    correlations: list[StoryCorrelation]
    total_correlations: int
    avg_similarity: float
    avg_time_to_mainstream: float | None = None
