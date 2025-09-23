"""
MongoDB document models for raw social media data.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field
from pymongo import ASCENDING, DESCENDING, TEXT, IndexModel


class SocialMediaPost(BaseModel):
    """Raw social media post document."""

    id: str = Field(alias="_id")
    platform: str  # twitter, reddit, tiktok, instagram
    external_id: str  # Platform-specific ID
    author_username: str
    author_display_name: str | None = None
    content: str
    url: str | None = None
    posted_at: datetime
    engagement: dict[str, int] = Field(default_factory=dict)  # likes, shares, comments
    metadata: dict[str, Any] = Field(default_factory=dict)  # Platform-specific data
    hashtags: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list)
    media_urls: list[str] = Field(default_factory=list)
    language: str = "en"
    sentiment_score: float | None = None
    processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class NewsArticle(BaseModel):
    """News article document."""

    id: str = Field(alias="_id")
    title: str
    content: str
    url: str
    source: str  # news outlet name
    author: str | None = None
    published_at: datetime
    category: str | None = None
    keywords: list[str] = Field(default_factory=list)
    entities: list[dict[str, Any]] = Field(default_factory=list)  # NER results
    sentiment_score: float | None = None
    credibility_score: float | None = None
    processed: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


class ProcessingQueue(BaseModel):
    """Queue item for processing pipeline."""

    id: str = Field(alias="_id")
    item_id: str
    item_type: str  # post, article, trend
    pipeline_stage: str  # ingestion, nlp, scoring, correlation
    priority: int = 1  # 1=low, 5=high
    attempts: int = 0
    max_attempts: int = 3
    error_message: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processing_started_at: datetime | None = None
    completed_at: datetime | None = None

    class Config:
        populate_by_name = True


class EmbeddingVector(BaseModel):
    """Document embeddings for similarity search."""

    id: str = Field(alias="_id")
    content_id: str  # Reference to post or article
    content_type: str  # post, article, story
    embedding: list[float]
    model_name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True


# MongoDB collection indexes
SOCIAL_MEDIA_POST_INDEXES = [
    IndexModel([("platform", ASCENDING)]),
    IndexModel([("external_id", ASCENDING)]),
    IndexModel([("author_username", ASCENDING)]),
    IndexModel([("posted_at", DESCENDING)]),
    IndexModel([("hashtags", ASCENDING)]),
    IndexModel([("processed", ASCENDING)]),
    IndexModel([("created_at", DESCENDING)]),
    IndexModel([("content", TEXT)]),  # Text search
    IndexModel([("platform", ASCENDING), ("posted_at", DESCENDING)]),  # Compound
]

NEWS_ARTICLE_INDEXES = [
    IndexModel([("source", ASCENDING)]),
    IndexModel([("published_at", DESCENDING)]),
    IndexModel([("category", ASCENDING)]),
    IndexModel([("keywords", ASCENDING)]),
    IndexModel([("processed", ASCENDING)]),
    IndexModel([("created_at", DESCENDING)]),
    IndexModel([("title", TEXT), ("content", TEXT)]),  # Text search
]

PROCESSING_QUEUE_INDEXES = [
    IndexModel([("pipeline_stage", ASCENDING)]),
    IndexModel([("priority", DESCENDING)]),
    IndexModel([("created_at", ASCENDING)]),
    IndexModel([("completed_at", ASCENDING)]),
    IndexModel([("pipeline_stage", ASCENDING), ("priority", DESCENDING)]),
]

EMBEDDING_VECTOR_INDEXES = [
    IndexModel([("content_id", ASCENDING)]),
    IndexModel([("content_type", ASCENDING)]),
    IndexModel([("model_name", ASCENDING)]),
    IndexModel([("created_at", DESCENDING)]),
]
