"""
Source service for managing source data and credibility tracking.
"""

from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from sqlalchemy.orm import selectinload

from app.models.sql_models import Source, CredibilityHistory, Mention
from app.schemas.source import (
    SourceResponse, SourceCreate, CredibilityHistoryResponse, 
    CredibilityHistoryPoint, PlatformStats, PlatformStatsResponse
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class SourceService:
    """Service for source-related operations."""
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def get_sources(
        self,
        skip: int = 0,
        limit: int = 50,
        platform: Optional[str] = None,
        verified_only: bool = False
    ) -> List[SourceResponse]:
        """Get sources with optional filtering."""
        
        query = select(Source)
        
        # Apply filters
        if platform:
            query = query.where(Source.platform == platform)
        
        if verified_only:
            query = query.where(Source.verified == True)
        
        # Order by credibility score
        query = query.order_by(desc(Source.credibility_score)).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        sources = result.scalars().all()
        
        return [SourceResponse.model_validate(source) for source in sources]
    
    async def get_source_by_id(self, source_id: str) -> Optional[SourceResponse]:
        """Get specific source by ID."""
        query = select(Source).where(Source.id == source_id)
        result = await self.db.execute(query)
        source = result.scalar_one_or_none()
        
        if source:
            return SourceResponse.model_validate(source)
        return None
    
    async def create_source(self, source_data: SourceCreate) -> SourceResponse:
        """Create a new source."""
        source = Source(**source_data.model_dump())
        
        self.db.add(source)
        await self.db.commit()
        await self.db.refresh(source)
        
        # Create initial credibility history entry
        history_entry = CredibilityHistory(
            source_id=source.id,
            credibility_score=source.credibility_score,
            reason="Initial source creation"
        )
        self.db.add(history_entry)
        await self.db.commit()
        
        logger.info(f"Created new source: {source.id} ({source.platform})")
        return SourceResponse.model_validate(source)
    
    async def get_credibility_history(
        self, 
        source_id: str, 
        days: int = 30
    ) -> Optional[CredibilityHistoryResponse]:
        """Get credibility score history for a source."""
        
        # Verify source exists
        source_query = select(Source).where(Source.id == source_id)
        source_result = await self.db.execute(source_query)
        source = source_result.scalar_one_or_none()
        
        if not source:
            return None
        
        # Get history within specified days
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        history_query = select(CredibilityHistory).where(
            and_(
                CredibilityHistory.source_id == source_id,
                CredibilityHistory.recorded_at >= cutoff_date
            )
        ).order_by(CredibilityHistory.recorded_at)
        
        history_result = await self.db.execute(history_query)
        history_data = history_result.scalars().all()
        
        if not history_data:
            # Return current score if no history
            history = [CredibilityHistoryPoint(
                credibility_score=source.credibility_score,
                reason="Current score",
                recorded_at=source.created_at
            )]
        else:
            history = [
                CredibilityHistoryPoint(
                    credibility_score=entry.credibility_score,
                    reason=entry.reason,
                    recorded_at=entry.recorded_at
                )
                for entry in history_data
            ]
        
        # Calculate statistics
        scores = [point.credibility_score for point in history]
        avg_score = sum(scores) / len(scores)
        
        # Determine trend
        if len(scores) >= 2:
            recent_avg = sum(scores[-3:]) / len(scores[-3:])
            older_avg = sum(scores[:-3]) / len(scores[:-3]) if len(scores) > 3 else scores[0]
            
            if recent_avg > older_avg + 5:
                trend = "improving"
            elif recent_avg < older_avg - 5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return CredibilityHistoryResponse(
            source_id=source.id,
            history=history,
            avg_score=avg_score,
            trend=trend
        )
    
    async def get_platform_stats(self) -> PlatformStatsResponse:
        """Get statistics breakdown by platform."""
        
        # Get overall platform stats
        platform_query = select(
            Source.platform,
            func.count(Source.id).label('total_sources'),
            func.count(func.nullif(Source.verified, False)).label('verified_sources'),
            func.avg(Source.credibility_score).label('avg_credibility')
        ).group_by(Source.platform).order_by(Source.platform)
        
        platform_result = await self.db.execute(platform_query)
        platform_data = platform_result.all()
        
        # Get active sources in last 24h
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        active_query = select(
            Source.platform,
            func.count(func.distinct(Source.id)).label('active_sources')
        ).select_from(
            Source
        ).join(
            Mention, Source.id == Mention.source_id
        ).where(
            Mention.posted_at >= cutoff_time
        ).group_by(Source.platform)
        
        active_result = await self.db.execute(active_query)
        active_data = {row.platform: row.active_sources for row in active_result.all()}
        
        # Combine data
        platforms = []
        total_sources = 0
        total_credibility_sum = 0
        
        for platform_info in platform_data:
            platform_stats = PlatformStats(
                platform=platform_info.platform,
                total_sources=platform_info.total_sources,
                verified_sources=platform_info.verified_sources or 0,
                avg_credibility=platform_info.avg_credibility or 50.0,
                active_sources_24h=active_data.get(platform_info.platform, 0)
            )
            platforms.append(platform_stats)
            total_sources += platform_info.total_sources
            total_credibility_sum += (platform_info.avg_credibility or 50.0) * platform_info.total_sources
        
        overall_avg_credibility = (
            total_credibility_sum / total_sources if total_sources > 0 else 50.0
        )
        
        return PlatformStatsResponse(
            platforms=platforms,
            total_sources=total_sources,
            overall_avg_credibility=overall_avg_credibility
        )
    
    async def update_credibility_score(
        self, 
        source_id: str, 
        new_score: float, 
        reason: Optional[str] = None
    ) -> bool:
        """Update source credibility score and record in history."""
        
        # Get source
        source_query = select(Source).where(Source.id == source_id)
        source_result = await self.db.execute(source_query)
        source = source_result.scalar_one_or_none()
        
        if not source:
            return False
        
        # Update score
        old_score = source.credibility_score
        source.credibility_score = new_score
        source.updated_at = datetime.utcnow()
        
        # Add history entry
        history_entry = CredibilityHistory(
            source_id=source_id,
            credibility_score=new_score,
            reason=reason or f"Score updated from {old_score} to {new_score}"
        )
        self.db.add(history_entry)
        
        await self.db.commit()
        logger.info(f"Updated credibility score for source {source_id}: {old_score} -> {new_score}")
        return True