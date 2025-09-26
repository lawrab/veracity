"""
Source schema definitions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID
else:
    # Import at runtime for Pydantic's model_validate
    from datetime import datetime
    from uuid import UUID


class SourceBase(BaseModel):
    """Base source schema."""

    platform: str = Field(..., max_length=50)
    username: str | None = Field(None, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    url: str | None = Field(None, max_length=500)
    verified: bool = False
    follower_count: int | None = None
    credibility_score: float = Field(default=50.0, ge=0.0, le=100.0)


class SourceCreate(SourceBase):
    """Schema for creating sources."""


class SourceUpdate(BaseModel):
    """Schema for updating sources."""

    display_name: str | None = Field(None, max_length=255)
    verified: bool | None = None
    follower_count: int | None = None
    credibility_score: float | None = Field(None, ge=0.0, le=100.0)


class SourceResponse(SourceBase):
    """Schema for source responses."""

    id: UUID
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class CredibilityHistoryPoint(BaseModel):
    """Schema for credibility history point."""

    credibility_score: float
    reason: str | None = None
    recorded_at: datetime


class CredibilityHistoryResponse(BaseModel):
    """Schema for credibility history response."""

    source_id: UUID
    history: list[CredibilityHistoryPoint]
    avg_score: float
    trend: str  # "improving", "declining", "stable"


class PlatformStats(BaseModel):
    """Schema for platform statistics."""

    platform: str
    total_sources: int
    verified_sources: int
    avg_credibility: float
    active_sources_24h: int


class PlatformStatsResponse(BaseModel):
    """Schema for platform stats response."""

    platforms: list[PlatformStats]
    total_sources: int
    overall_avg_credibility: float
