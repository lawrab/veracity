"""
Trend service for managing trend data and operations.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.sql_models import Mention, Source, Story, Trend
from app.schemas.trend import TrendCreate, TrendEvolution, TrendResponse, TrendSource

logger = get_logger(__name__)


class TrendService:
    """Service for trend-related operations."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def get_trending(
        self,
        skip: int = 0,
        limit: int = 10,
        platform: Optional[str] = None,
        time_window: str = "1h",
    ) -> List[TrendResponse]:
        """Get trending topics with optional filtering."""

        # Calculate time window
        time_windows = {
            "1h": timedelta(hours=1),
            "6h": timedelta(hours=6),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
        }

        window_delta = time_windows.get(time_window, timedelta(hours=1))
        cutoff_time = datetime.utcnow() - window_delta

        # Build query
        query = select(Trend).where(Trend.detected_at >= cutoff_time)

        if platform:
            query = query.where(Trend.platforms.contains([platform]))

        # Order by velocity (trending strength)
        query = query.order_by(Trend.velocity.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        trends = result.scalars().all()

        return [TrendResponse.model_validate(trend) for trend in trends]

    async def get_trend_by_id(self, trend_id: str) -> Optional[TrendResponse]:
        """Get specific trend by ID."""
        query = select(Trend).where(Trend.id == trend_id)
        result = await self.db.execute(query)
        trend = result.scalar_one_or_none()

        if trend:
            return TrendResponse.model_validate(trend)
        return None

    async def create_trend(self, trend_data: TrendCreate) -> TrendResponse:
        """Create a new trend."""
        trend = Trend(**trend_data.model_dump(), detected_at=datetime.utcnow())

        self.db.add(trend)
        await self.db.commit()
        await self.db.refresh(trend)

        logger.info(f"Created new trend: {trend.id}")
        return TrendResponse.model_validate(trend)

    async def get_trend_evolution(self, trend_id: str) -> Optional[TrendEvolution]:
        """Get trend evolution data over time."""

        # Get the trend first
        trend_query = select(Trend).where(Trend.id == trend_id)
        trend_result = await self.db.execute(trend_query)
        trend = trend_result.scalar_one_or_none()

        if not trend:
            return None

        # Get mentions over time (hourly buckets)
        mentions_query = (
            select(
                func.date_trunc("hour", Mention.posted_at).label("hour"),
                func.count(Mention.id).label("mention_count"),
                func.avg(Mention.sentiment_score).label("avg_sentiment"),
            )
            .where(Mention.trend_id == trend_id)
            .group_by(func.date_trunc("hour", Mention.posted_at))
            .order_by("hour")
        )

        mentions_result = await self.db.execute(mentions_query)
        hourly_data = mentions_result.all()

        if not hourly_data:
            return TrendEvolution(
                timestamps=[trend.detected_at],
                mention_counts=[trend.mention_count],
                velocity_values=[trend.velocity],
                sentiment_scores=[trend.sentiment_score],
            )

        # Calculate velocity for each hour
        timestamps = []
        mention_counts = []
        velocity_values = []
        sentiment_scores = []

        prev_count = 0
        for hour_data in hourly_data:
            timestamps.append(hour_data.hour)
            mention_counts.append(hour_data.mention_count)
            velocity_values.append(max(0, hour_data.mention_count - prev_count))
            sentiment_scores.append(hour_data.avg_sentiment)
            prev_count = hour_data.mention_count

        return TrendEvolution(
            timestamps=timestamps,
            mention_counts=mention_counts,
            velocity_values=velocity_values,
            sentiment_scores=sentiment_scores,
        )

    async def get_trend_sources(self, trend_id: str) -> Optional[List[TrendSource]]:
        """Get sources contributing to a trend."""

        # Verify trend exists
        trend_query = select(Trend).where(Trend.id == trend_id)
        trend_result = await self.db.execute(trend_query)
        trend = trend_result.scalar_one_or_none()

        if not trend:
            return None

        # Get source breakdown
        sources_query = (
            select(
                Source.platform,
                func.count(func.distinct(Source.id)).label("source_count"),
                func.count(Mention.id).label("mention_count"),
                func.avg(Source.credibility_score).label("avg_credibility"),
            )
            .select_from(Mention)
            .join(Source, Mention.source_id == Source.id)
            .where(Mention.trend_id == trend_id)
            .group_by(Source.platform)
            .order_by(func.count(Mention.id).desc())
        )

        sources_result = await self.db.execute(sources_query)
        platform_data = sources_result.all()

        trend_sources = []
        for platform_info in platform_data:
            # Get top sources for this platform
            top_sources_query = (
                select(
                    Source.username,
                    Source.display_name,
                    Source.credibility_score,
                    func.count(Mention.id).label("mention_count"),
                )
                .select_from(Mention)
                .join(Source, Mention.source_id == Source.id)
                .where(
                    and_(
                        Mention.trend_id == trend_id,
                        Source.platform == platform_info.platform,
                    )
                )
                .group_by(
                    Source.id,
                    Source.username,
                    Source.display_name,
                    Source.credibility_score,
                )
                .order_by(func.count(Mention.id).desc())
                .limit(5)
            )

            top_sources_result = await self.db.execute(top_sources_query)
            top_sources = [
                {
                    "username": src.username,
                    "display_name": src.display_name,
                    "credibility_score": src.credibility_score,
                    "mention_count": src.mention_count,
                }
                for src in top_sources_result.all()
            ]

            trend_sources.append(
                TrendSource(
                    platform=platform_info.platform,
                    source_count=platform_info.source_count,
                    mention_count=platform_info.mention_count,
                    avg_credibility=platform_info.avg_credibility or 50.0,
                    top_sources=top_sources,
                )
            )

        return trend_sources
