"""
Trust Scoring API Endpoints

Provides REST API for trust score calculations, bot detection,
and trust score management.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.database import get_postgres_session
from app.services.scoring.trust_scorer import TrustScorer
from app.services.story_service import StoryService
from app.services.websocket_manager import websocket_manager

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["trust-scoring"])


class TrustScoreRequest(BaseModel):
    """Request schema for trust score calculation."""

    story_id: str


class BotDetectionRequest(BaseModel):
    """Request schema for bot detection analysis."""

    posts: list[dict[str, Any]] = Field(
        ..., description="Social media posts to analyze"
    )


class TrustScoreResponse(BaseModel):
    """Response schema for trust score results."""

    score: float = Field(..., ge=0.0, le=1.0, description="Trust score (0-1)")
    score_percentage: float = Field(
        ..., ge=0.0, le=100.0, description="Trust score as percentage"
    )
    signals: dict[str, dict[str, Any]] = Field(
        ..., description="Individual trust signals"
    )
    explanation: list[str] = Field(..., description="Human-readable explanations")
    calculated_at: str = Field(..., description="Calculation timestamp")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the score"
    )


class BotDetectionResponse(BaseModel):
    """Response schema for bot detection results."""

    bot_probability: float = Field(
        ..., ge=0.0, le=1.0, description="Bot probability score"
    )
    coordinated_campaign: bool = Field(
        ..., description="Whether coordinated campaign detected"
    )
    suspicious_accounts: list[dict[str, Any]] = Field(
        ..., description="List of suspicious accounts"
    )
    total_accounts_analyzed: int = Field(..., description="Total accounts analyzed")
    analysis: str = Field(..., description="Analysis summary")


@router.post("/calculate", response_model=TrustScoreResponse)
async def calculate_trust_score(
    request: TrustScoreRequest, db: AsyncSession = Depends(get_postgres_session)
):
    """
    Calculate trust score for a specific story.

    Analyzes multiple signals including source credibility, velocity patterns,
    cross-platform correlation, and engagement authenticity to generate
    a comprehensive trust score.
    """
    try:
        # Get story
        story_service = StoryService(db)
        story = await story_service.get_story_by_id(request.story_id)

        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        # Calculate trust score
        trust_scorer = TrustScorer()
        score_result = await trust_scorer.calculate_score(story)

        # Store trust signals in database
        signals_for_db = []
        for signal_type, signal_data in score_result["signals"].items():
            if signal_data["value"] is not None:
                signals_for_db.append(
                    {
                        "type": signal_type,
                        "value": signal_data["value"],
                        "weight": signal_data["weight"],
                        "explanation": f"{signal_type}: {signal_data['value']:.3f}",
                    }
                )

        # Update story trust score
        await story_service.update_trust_score(
            request.story_id,
            score_result["score"] * 100,  # Convert to 0-100 scale for DB
            signals_for_db,
        )

        # Broadcast update via WebSocket
        await websocket_manager.broadcast_trust_score_update(
            request.story_id, score_result["score_percentage"], score_result["signals"]
        )

        logger.info(
            "Calculated trust score for story %s: %.1f%%",
            request.story_id,
            score_result["score_percentage"],
        )

        return TrustScoreResponse(**score_result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error calculating trust score: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/bot-detection", response_model=BotDetectionResponse)
async def detect_bots(request: BotDetectionRequest):
    """
    Analyze posts for bot activity and coordinated campaigns.

    Examines posting patterns, engagement ratios, timing analysis,
    and content similarity to identify potential bot networks
    and coordinated inauthentic behavior.
    """
    try:
        if not request.posts:
            raise HTTPException(
                status_code=400, detail="No posts provided for analysis"
            )

        if len(request.posts) > 1000:
            raise HTTPException(status_code=400, detail="Too many posts (max 1000)")

        # Perform bot detection
        trust_scorer = TrustScorer()
        detection_result = await trust_scorer.detect_bots(request.posts)

        logger.info(
            "Bot detection: %.3f probability, %d suspicious accounts",
            detection_result["bot_probability"],
            len(detection_result["suspicious_accounts"]),
        )

        return BotDetectionResponse(**detection_result)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in bot detection: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/story/{story_id}/score", response_model=TrustScoreResponse)
async def get_current_trust_score(
    story_id: str,
    recalculate: bool = Query(False, description="Whether to recalculate score"),
    db: AsyncSession = Depends(get_postgres_session),
):
    """
    Get current trust score for a story.

    Returns the most recent trust score calculation. If recalculate=true,
    performs a fresh calculation instead of returning cached results.
    """
    try:
        story_service = StoryService(db)
        story = await story_service.get_story_by_id(story_id)

        if not story:
            raise HTTPException(status_code=404, detail="Story not found")

        if recalculate:
            # Perform fresh calculation
            trust_scorer = TrustScorer()
            score_result = await trust_scorer.calculate_score(story)

            # Update database
            signals_for_db = []
            for signal_type, signal_data in score_result["signals"].items():
                if signal_data["value"] is not None:
                    signals_for_db.append(
                        {
                            "type": signal_type,
                            "value": signal_data["value"],
                            "weight": signal_data["weight"],
                            "explanation": f"{signal_type}: {signal_data['value']:.3f}",
                        }
                    )

            await story_service.update_trust_score(
                story_id, score_result["score"] * 100, signals_for_db
            )

            return TrustScoreResponse(**score_result)
        # Return current score from database
        return TrustScoreResponse(
            score=story.trust_score / 100.0,  # Convert from 0-100 to 0-1
            score_percentage=story.trust_score,
            signals={},
            explanation=[f"Current trust score: {story.trust_score:.1f}%"],
            calculated_at=story.last_updated_at.isoformat(),
            confidence=0.8,  # Default confidence for stored scores
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting trust score: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/leaderboard")
async def get_trust_leaderboard(
    limit: int = Query(10, ge=1, le=100, description="Number of top stories to return"),
    category: str | None = Query(None, description="Filter by story category"),
    db: AsyncSession = Depends(get_postgres_session),
):
    """
    Get stories ranked by trust score.

    Returns the highest-scoring stories based on trust analysis,
    useful for identifying the most credible content.
    """
    try:
        story_service = StoryService(db)

        # Get top stories by trust score
        stories = await story_service.get_stories(
            skip=0, limit=limit, trust_score_min=0.0, category=category
        )

        # Sort by trust score (descending)
        sorted_stories = sorted(stories, key=lambda s: s.trust_score, reverse=True)

        return {
            "stories": [
                {
                    "id": story.id,
                    "title": story.title,
                    "trust_score": story.trust_score,
                    "trust_score_normalized": story.trust_score / 100.0,
                    "category": story.category,
                    "velocity": story.velocity,
                    "last_updated": story.last_updated_at,
                    "created_at": story.created_at,
                }
                for story in sorted_stories
            ],
            "total": len(sorted_stories),
            "category_filter": category,
            "generated_at": story_service.db.get_bind()
            .execute("SELECT NOW()")
            .scalar(),
        }

    except Exception as e:
        logger.exception(f"Error getting trust leaderboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class BulkCalculateRequest(BaseModel):
    """Request schema for bulk trust score calculation."""

    story_ids: list[str] = Field(
        ..., max_items=50, description="List of story IDs to process"
    )


@router.post("/bulk-calculate")
async def bulk_calculate_trust_scores(
    request: BulkCalculateRequest, db: AsyncSession = Depends(get_postgres_session)
):
    """
    Calculate trust scores for multiple stories in bulk.

    Efficiently processes multiple stories for trust score calculation.
    Limited to 50 stories per request to prevent performance issues.
    """
    try:
        if len(request.story_ids) > 50:
            raise HTTPException(status_code=400, detail="Too many stories (max 50)")

        story_service = StoryService(db)
        trust_scorer = TrustScorer()

        results = []
        errors = []

        for story_id in request.story_ids:
            try:
                # Get story
                story = await story_service.get_story_by_id(story_id)
                if not story:
                    errors.append(f"Story {story_id} not found")
                    continue

                # Calculate score
                score_result = await trust_scorer.calculate_score(story)

                # Update database
                signals_for_db = []
                for signal_type, signal_data in score_result["signals"].items():
                    if signal_data["value"] is not None:
                        signals_for_db.append(
                            {
                                "type": signal_type,
                                "value": signal_data["value"],
                                "weight": signal_data["weight"],
                                "explanation": (
                                    f"{signal_type}: {signal_data['value']:.3f}"
                                ),
                            }
                        )

                await story_service.update_trust_score(
                    story_id, score_result["score"] * 100, signals_for_db
                )

                results.append(
                    {
                        "story_id": story_id,
                        "trust_score": score_result["score_percentage"],
                        "confidence": score_result["confidence"],
                    }
                )

            except Exception as e:
                errors.append(f"Error processing story {story_id}: {e!s}")

        logger.info(
            "Bulk trust calculation: %d success, %d errors",
            len(results),
            len(errors),
        )

        return {
            "processed": len(results),
            "errors": len(errors),
            "results": results,
            "error_details": errors,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in bulk trust score calculation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


class TrustScoreStatistics(BaseModel):
    """Trust score statistics response."""

    average_score: float = Field(..., description="Average trust score percentage")
    total_stories: int = Field(..., description="Total stories with trust scores")
    high_trust_count: int = Field(..., description="Stories with trust score >= 80%")
    medium_trust_count: int = Field(..., description="Stories with trust score 50-80%")
    low_trust_count: int = Field(..., description="Stories with trust score < 50%")
    score_trend: float = Field(..., description="Score change percentage")


@router.get("/statistics", response_model=TrustScoreStatistics)
async def get_trust_score_statistics(db: AsyncSession = Depends(get_postgres_session)):
    """
    Get trust score statistics across all stories.

    Returns average trust score, distribution, and trend information
    for dashboard display and analytics.
    """
    try:
        story_service = StoryService(db)

        # Get all stories with trust scores (adjust limit as needed)
        stories = await story_service.get_stories(
            skip=0,
            limit=1000,  # Get recent stories for statistics
            trust_score_min=0.0,
        )

        if not stories:
            return TrustScoreStatistics(
                average_score=0.0,
                total_stories=0,
                high_trust_count=0,
                medium_trust_count=0,
                low_trust_count=0,
                score_trend=0.0,
            )

        # Calculate statistics
        trust_scores = [
            story.trust_score for story in stories if story.trust_score is not None
        ]

        if not trust_scores:
            return TrustScoreStatistics(
                average_score=0.0,
                total_stories=len(stories),
                high_trust_count=0,
                medium_trust_count=0,
                low_trust_count=0,
                score_trend=0.0,
            )

        average_score = sum(trust_scores) / len(trust_scores)

        # Count by trust level
        high_trust = len([s for s in trust_scores if s >= 80])
        medium_trust = len([s for s in trust_scores if 50 <= s < 80])
        low_trust = len([s for s in trust_scores if s < 50])

        # Calculate trend (simplified - compare recent vs older stories)
        mid_point = len(trust_scores) // 2
        if mid_point > 0:
            recent_avg = sum(trust_scores[:mid_point]) / mid_point
            older_avg = sum(trust_scores[mid_point:]) / (len(trust_scores) - mid_point)
            score_trend = (
                ((recent_avg - older_avg) / older_avg) * 100 if older_avg > 0 else 0.0
            )
        else:
            score_trend = 0.0

        logger.info(
            "Trust score statistics: avg=%.1f%%, total=%d stories, trend=%.1f%%",
            average_score,
            len(trust_scores),
            score_trend,
        )

        return TrustScoreStatistics(
            average_score=round(average_score, 1),
            total_stories=len(trust_scores),
            high_trust_count=high_trust,
            medium_trust_count=medium_trust,
            low_trust_count=low_trust,
            score_trend=round(score_trend, 1),
        )

    except Exception as e:
        logger.exception(f"Error getting trust score statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
