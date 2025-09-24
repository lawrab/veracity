"""
Schemas for ingestion API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class CollectorStatus(str, Enum):
    """Status of a data collector."""

    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"


class IngestionRequest(BaseModel):
    """Request model for data ingestion."""

    sources: list[str] = Field(
        ..., description="List of sources to collect from (subreddits, keywords, etc.)"
    )
    limit: int | None = Field(
        100, description="Maximum number of items to collect per source"
    )


class IngestionResponse(BaseModel):
    """Response model for data ingestion."""

    message: str
    job_id: str
    status: str


class IngestionStatus(BaseModel):
    """Status of all data collectors."""

    collectors: dict[str, CollectorStatus]
    last_update: datetime = Field(default_factory=datetime.utcnow)


class CollectedDataSummary(BaseModel):
    """Summary of collected data."""

    platform: str
    count: int
    oldest: datetime | None = None
    newest: datetime | None = None
    topics: list[str] = []
