"""
Story service for managing story data and operations.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.sql_models import Correlation, Story, Trend, TrustSignal
from app.schemas.story import (
    StoryCorrelation,
    StoryCorrelationsResponse,
    StoryCreate,
    StoryResponse,
    TrustScoreHistory,
)

logger = get_logger(__name__)


class StoryService:
    """Service for story-related operations."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_stories(
        self,
        skip: int = 0,
        limit: int = 10,
        trust_score_min: Optional[float] = None,
        category: Optional[str] = None,
    ) -> List[StoryResponse]:
        """Get stories with optional filtering."""

        query = select(Story)

        # Apply filters
        if trust_score_min is not None:
            query = query.where(Story.trust_score >= trust_score_min)

        if category:
            query = query.where(Story.category == category)

        # Order by most recent activity
        query = query.order_by(desc(Story.last_updated_at)).offset(skip).limit(limit)

        result = await self.db.execute(query)
        stories = result.scalars().all()

        return [StoryResponse.model_validate(story) for story in stories]

    async def get_story_by_id(self, story_id: str) -> Optional[StoryResponse]:
        """Get specific story by ID."""
        query = select(Story).where(Story.id == story_id)
        result = await self.db.execute(query)
        story = result.scalar_one_or_none()

        if story:
            return StoryResponse.model_validate(story)
        return None

    async def create_story(self, story_data: StoryCreate) -> StoryResponse:
        """Create a new story."""
        story = Story(**story_data.model_dump(), last_updated_at=datetime.utcnow())

        self.db.add(story)
        await self.db.commit()
        await self.db.refresh(story)

        logger.info(f"Created new story: {story.id}")
        return StoryResponse.model_validate(story)

    async def get_trust_score_history(
        self, story_id: str
    ) -> Optional[TrustScoreHistory]:
        """Get trust score history for a story."""

        # Verify story exists
        story_query = select(Story).where(Story.id == story_id)
        story_result = await self.db.execute(story_query)
        story = story_result.scalar_one_or_none()

        if not story:
            return None

        # Get trust signals over time
        signals_query = (
            select(
                TrustSignal.calculated_at,
                TrustSignal.signal_type,
                TrustSignal.value,
                TrustSignal.weight,
                TrustSignal.explanation,
            )
            .where(TrustSignal.story_id == story_id)
            .order_by(TrustSignal.calculated_at)
        )

        signals_result = await self.db.execute(signals_query)
        signals_data = signals_result.all()

        if not signals_data:
            return TrustScoreHistory(
                timestamps=[story.created_at], scores=[story.trust_score], signals=[{}]
            )

        # Group signals by timestamp and calculate composite scores
        timestamp_groups = {}
        for signal in signals_data:
            ts = signal.calculated_at
            if ts not in timestamp_groups:
                timestamp_groups[ts] = []
            timestamp_groups[ts].append(
                {
                    "type": signal.signal_type,
                    "value": signal.value,
                    "weight": signal.weight,
                    "explanation": signal.explanation,
                }
            )

        timestamps = sorted(timestamp_groups.keys())
        scores = []
        signals = []

        for ts in timestamps:
            ts_signals = timestamp_groups[ts]
            # Calculate weighted score for this timestamp
            total_weighted_value = sum(s["value"] * s["weight"] for s in ts_signals)
            total_weight = sum(s["weight"] for s in ts_signals)
            composite_score = (
                total_weighted_value / total_weight if total_weight > 0 else 0
            )

            scores.append(min(100, max(0, composite_score)))
            signals.append(ts_signals)

        return TrustScoreHistory(timestamps=timestamps, scores=scores, signals=signals)

    async def get_story_correlations(
        self, story_id: str
    ) -> Optional[StoryCorrelationsResponse]:
        """Get correlations between social trends and mainstream news."""

        # Verify story exists
        story_query = select(Story).where(Story.id == story_id)
        story_result = await self.db.execute(story_query)
        story = story_result.scalar_one_or_none()

        if not story:
            return None

        # Get correlations
        correlations_query = (
            select(Correlation)
            .where(Correlation.story_id == story_id)
            .order_by(desc(Correlation.similarity_score))
        )

        correlations_result = await self.db.execute(correlations_query)
        correlations_data = correlations_result.scalars().all()

        correlations = [
            StoryCorrelation(
                news_article_url=corr.news_article_url,
                news_source=corr.news_source,
                news_title=corr.news_title,
                similarity_score=corr.similarity_score,
                time_to_mainstream_hours=corr.time_to_mainstream_hours,
                found_at=corr.found_at,
            )
            for corr in correlations_data
        ]

        # Calculate statistics
        total_correlations = len(correlations)
        avg_similarity = (
            sum(c.similarity_score for c in correlations) / total_correlations
            if total_correlations > 0
            else 0
        )

        mainstream_times = [
            c.time_to_mainstream_hours
            for c in correlations
            if c.time_to_mainstream_hours is not None
        ]
        avg_time_to_mainstream = (
            sum(mainstream_times) / len(mainstream_times) if mainstream_times else None
        )

        return StoryCorrelationsResponse(
            correlations=correlations,
            total_correlations=total_correlations,
            avg_similarity=avg_similarity,
            avg_time_to_mainstream=avg_time_to_mainstream,
        )

    async def update_trust_score(
        self, story_id: str, new_score: float, signals: List[Dict[str, Any]]
    ) -> bool:
        """Update story trust score and add trust signals."""

        # Update story
        story_query = select(Story).where(Story.id == story_id)
        story_result = await self.db.execute(story_query)
        story = story_result.scalar_one_or_none()

        if not story:
            return False

        story.trust_score = new_score
        story.last_updated_at = datetime.utcnow()

        # Add trust signals
        for signal_data in signals:
            trust_signal = TrustSignal(
                story_id=story_id,
                signal_type=signal_data["type"],
                value=signal_data["value"],
                weight=signal_data.get("weight", 1.0),
                explanation=signal_data.get("explanation"),
                calculated_at=datetime.utcnow(),
            )
            self.db.add(trust_signal)

        await self.db.commit()
        logger.info(f"Updated trust score for story {story_id}: {new_score}")
        return True
