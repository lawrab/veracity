"""
Trust scoring schemas.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class TrustScoreUpdate(BaseModel):
    """Schema for trust score updates."""

    story_id: UUID
    overall_score: float = Field(..., ge=0.0, le=1.0)
    source_credibility: float | None = Field(None, ge=0.0, le=1.0)
    content_consistency: float | None = Field(None, ge=0.0, le=1.0)
    social_verification: float | None = Field(None, ge=0.0, le=1.0)
    expert_validation: float | None = Field(None, ge=0.0, le=1.0)
    factors: dict[str, float] | None = None