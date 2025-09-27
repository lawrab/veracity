"""
Schemas for pipeline operations.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class PipelineTriggerRequest(BaseModel):
    """Request to trigger pipeline execution."""
    
    subreddits: list[str] | None = Field(
        default=None,
        description="List of subreddits to monitor. If None, uses defaults.",
        examples=[["worldnews", "technology", "science"]],
    )
    limit: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum posts per subreddit",
    )


class URLAnalysisRequest(BaseModel):
    """Request to analyze a specific URL."""
    
    url: HttpUrl = Field(
        description="URL to analyze for trustability",
        examples=["https://example.com/news/article"],
    )
    user_id: str | None = Field(
        default=None,
        description="Optional user ID for tracking",
    )


class PipelineResponse(BaseModel):
    """Response from pipeline operations."""
    
    task_id: str = Field(description="Celery task ID for tracking")
    status: str = Field(description="Current status of the task")
    message: str = Field(description="Human-readable status message")


class TaskStatus(BaseModel):
    """Status of a specific task."""
    
    task_id: str
    status: str = Field(
        description="Task status: PENDING, STARTED, SUCCESS, FAILURE, RETRY, REVOKED"
    )
    message: str | None = None
    current: int | None = Field(default=None, description="Current progress")
    total: int | None = Field(default=None, description="Total items to process")
    result: dict[str, Any] | None = Field(default=None, description="Task result if completed")
    error: str | None = Field(default=None, description="Error message if failed")


class PipelineStatus(BaseModel):
    """Overall pipeline system status."""
    
    workers_online: int = Field(description="Number of Celery workers online")
    active_tasks: int = Field(description="Number of currently running tasks")
    scheduled_tasks: int = Field(description="Number of scheduled tasks")
    pipeline_enabled: bool = Field(description="Whether pipeline is operational")