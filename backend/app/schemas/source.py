"""
Source schema definitions.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SourceBase(BaseModel):
    """Base source schema."""

    platform: str = Field(..., max_length=50)
    username: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    url: Optional[str] = Field(None, max_length=500)
    verified: bool = False
    follower_count: Optional[int] = None
    credibility_score: float = Field(default=50.0, ge=0.0, le=100.0)


class SourceCreate(SourceBase):
    """Schema for creating sources."""

    pass


class SourceUpdate(BaseModel):
    """Schema for updating sources."""

    display_name: Optional[str] = Field(None, max_length=255)
    verified: Optional[bool] = None
    follower_count: Optional[int] = None
    credibility_score: Optional[float] = Field(None, ge=0.0, le=100.0)


class SourceResponse(SourceBase):
    """Schema for source responses."""

    id: UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CredibilityHistoryPoint(BaseModel):
    """Schema for credibility history point."""

    credibility_score: float
    reason: Optional[str] = None
    recorded_at: datetime


class CredibilityHistoryResponse(BaseModel):
    """Schema for credibility history response."""

    source_id: UUID
    history: List[CredibilityHistoryPoint]
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

    platforms: List[PlatformStats]
    total_sources: int
    overall_avg_credibility: float
