"""
SQLAlchemy models for PostgreSQL database.
"""

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Source(Base):
    """Source model for tracking credibility of sources."""

    __tablename__ = "sources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(
        String(50), nullable=False, index=True
    )  # twitter, reddit, news_site
    username = Column(String(255), nullable=True, index=True)
    display_name = Column(String(255), nullable=True)
    url = Column(String(500), nullable=True)
    verified = Column(Boolean, default=False)
    follower_count = Column(Integer, nullable=True)
    credibility_score = Column(Float, default=50.0)  # 0-100 scale
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    mentions = relationship("Mention", back_populates="source")
    credibility_history = relationship("CredibilityHistory", back_populates="source")


class Story(Base):
    """Story model representing aggregated narratives."""

    __tablename__ = "stories"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True)
    trust_score = Column(Float, default=0.0)  # 0-100 scale
    velocity = Column(Float, default=0.0)  # mentions per hour
    geographic_spread = Column(JSON, nullable=True)  # {"US": 45, "UK": 20, ...}
    first_seen_at = Column(DateTime(timezone=True), nullable=False)
    last_updated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    trends = relationship("Trend", back_populates="story")
    trust_signals = relationship("TrustSignal", back_populates="story")
    correlations = relationship("Correlation", back_populates="story")


class Trend(Base):
    """Trend model for tracking emerging narratives."""

    __tablename__ = "trends"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), nullable=True)
    keywords = Column(ARRAY(String), nullable=False, index=True)
    hashtags = Column(ARRAY(String), nullable=True)
    platforms = Column(ARRAY(String), nullable=False)  # ["twitter", "reddit"]
    mention_count = Column(Integer, default=0)
    velocity = Column(Float, default=0.0)  # mentions per minute
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    peak_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    story = relationship("Story", back_populates="trends")
    mentions = relationship("Mention", back_populates="trend")


class Mention(Base):
    """Individual social media posts/articles."""

    __tablename__ = "mentions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    trend_id = Column(UUID(as_uuid=True), ForeignKey("trends.id"), nullable=True)
    external_id = Column(String(255), nullable=False)  # Platform-specific ID
    content = Column(Text, nullable=False)
    url = Column(String(500), nullable=True)
    engagement_count = Column(Integer, default=0)  # likes, shares, etc.
    sentiment_score = Column(Float, nullable=True)
    language = Column(String(10), default="en")
    posted_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source = relationship("Source", back_populates="mentions")
    trend = relationship("Trend", back_populates="mentions")


class TrustSignal(Base):
    """Trust signals contributing to story credibility."""

    __tablename__ = "trust_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), nullable=False)
    signal_type = Column(
        String(100), nullable=False
    )  # source_diversity, velocity, etc.
    value = Column(Float, nullable=False)
    weight = Column(Float, default=1.0)
    explanation = Column(Text, nullable=True)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    story = relationship("Story", back_populates="trust_signals")


class Correlation(Base):
    """Correlations between social trends and mainstream news."""

    __tablename__ = "correlations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id = Column(UUID(as_uuid=True), ForeignKey("stories.id"), nullable=False)
    news_article_url = Column(String(500), nullable=False)
    news_source = Column(String(255), nullable=False)
    news_title = Column(String(500), nullable=False)
    similarity_score = Column(Float, nullable=False)  # 0-1
    time_to_mainstream_hours = Column(Float, nullable=True)
    found_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    story = relationship("Story", back_populates="correlations")


class CredibilityHistory(Base):
    """Historical credibility scores for sources."""

    __tablename__ = "credibility_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("sources.id"), nullable=False)
    credibility_score = Column(Float, nullable=False)
    reason = Column(String(255), nullable=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    source = relationship("Source", back_populates="credibility_history")
