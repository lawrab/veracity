"""
Trust Scoring Engine

Implements multi-signal trust scoring algorithm for evaluating story credibility.
Combines source credibility, velocity patterns, engagement analysis, and cross-platform
correlation to generate dynamic trust scores.
"""

from __future__ import annotations

import logging
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.schemas.story import StoryResponse

logger = logging.getLogger(__name__)


class TrustScorer:
    """
    Multi-signal trust scoring engine for story credibility assessment.

    Implements a weighted scoring algorithm that considers:
    - Source credibility and historical accuracy
    - Velocity patterns and viral spread analysis
    - Cross-platform correlation strength
    - Engagement pattern authenticity
    - Bot detection and coordinated campaign analysis
    """

    def __init__(self):
        self.signal_weights = {
            "source_credibility": 0.25,
            "velocity_pattern": 0.20,
            "cross_platform_correlation": 0.20,
            "engagement_authenticity": 0.15,
            "temporal_consistency": 0.10,
            "content_quality": 0.10,
        }

        # Bot detection thresholds
        self.bot_detection_thresholds = {
            "engagement_ratio_anomaly": 0.8,  # Likes/retweets ratio
            "account_age_days": 30,
            "posting_frequency_per_hour": 10,
            "content_similarity": 0.9,
            "coordinated_timing_window": 300,  # seconds
        }

    async def calculate_score(self, story: StoryResponse) -> dict[str, Any]:
        """
        Calculate comprehensive trust score for a story.

        Args:
            story: Story object to score

        Returns:
            Dict containing score, signals, and explanation
        """
        signals = {}
        explanations = []

        try:
            # Calculate individual trust signals
            signals["source_credibility"] = await self._calculate_source_credibility(
                story
            )
            signals["velocity_pattern"] = await self._analyze_velocity_pattern(story)
            signals[
                "cross_platform_correlation"
            ] = await self._analyze_cross_platform_correlation(story)
            signals[
                "engagement_authenticity"
            ] = await self._analyze_engagement_authenticity(story)
            signals["temporal_consistency"] = await self._analyze_temporal_consistency(
                story
            )
            signals["content_quality"] = await self._analyze_content_quality(story)

            # Calculate weighted composite score
            composite_score = 0.0
            total_weight = 0.0

            for signal_type, value in signals.items():
                if value is not None:
                    weight = self.signal_weights[signal_type]
                    composite_score += value * weight
                    total_weight += weight

                    # Generate explanation
                    explanations.append(
                        self._generate_signal_explanation(signal_type, value)
                    )

            # Normalize score
            final_score = composite_score / total_weight if total_weight > 0 else 0.5
            final_score = max(0.0, min(1.0, final_score))  # Clamp to [0, 1]

            return {
                "score": final_score,
                "score_percentage": round(final_score * 100, 1),
                "signals": {
                    k: {
                        "value": v,
                        "weight": self.signal_weights[k],
                        "contribution": (
                            v * self.signal_weights[k] if v is not None else 0
                        ),
                    }
                    for k, v in signals.items()
                },
                "explanation": explanations,
                "calculated_at": datetime.now(timezone.utc).isoformat(),
                "confidence": self._calculate_confidence(signals),
            }

        except Exception as e:
            logger.exception(f"Error calculating trust score for story {story.id}: {e}")
            return {
                "score": 0.5,
                "score_percentage": 50.0,
                "signals": {},
                "explanation": ["Error calculating trust score"],
                "calculated_at": datetime.now(timezone.utc).isoformat(),
                "confidence": 0.0,
            }

    async def _calculate_source_credibility(self, _story: StoryResponse) -> float | None:
        """Calculate source credibility score based on historical accuracy."""
        # This would integrate with source tracking
        # For now, return a baseline score based on source diversity
        try:
            # Simple implementation: more diverse sources = higher credibility
            # In production, this would query CredibilityHistory table
            return 0.7  # Placeholder
        except Exception as e:
            logger.exception(f"Error calculating source credibility: {e}")
            return None

    async def _analyze_velocity_pattern(self, story: StoryResponse) -> float | None:
        """Analyze story velocity pattern for authenticity."""
        try:
            velocity = story.velocity

            if velocity is None:
                return None

            # Analyze velocity pattern (organic vs. artificial)
            # Natural viral content follows power law distribution
            # Artificial amplification shows sudden spikes

            if velocity < 0.1:
                return 0.8  # Slow, organic spread
            if velocity < 1.0:
                return 0.9  # Moderate viral spread
            if velocity < 10.0:
                return 0.6  # Fast spread - could be artificial
            return 0.3  # Very fast - likely artificial amplification

        except Exception as e:
            logger.exception(f"Error analyzing velocity pattern: {e}")
            return None

    async def _analyze_cross_platform_correlation(
        self, _story: StoryResponse
    ) -> float | None:
        """Analyze correlation across multiple platforms."""
        try:
            # This would analyze trends across Twitter, Reddit, TikTok, etc.
            # Organic stories tend to appear across multiple platforms naturally
            # Coordinated campaigns often focus on single platforms initially

            # Placeholder implementation
            return 0.75

        except Exception as e:
            logger.exception(f"Error analyzing cross-platform correlation: {e}")
            return None

    async def _analyze_engagement_authenticity(
        self, _story: StoryResponse
    ) -> float | None:
        """Analyze engagement patterns for bot detection."""
        try:
            # Analyze engagement ratios, timing patterns, account diversity
            # Authentic engagement shows natural distribution
            # Bot networks show coordinated patterns

            # Placeholder implementation
            return 0.8

        except Exception as e:
            logger.exception(f"Error analyzing engagement authenticity: {e}")
            return None

    async def _analyze_temporal_consistency(self, story: StoryResponse) -> float | None:
        """Analyze temporal consistency of story evolution."""
        try:
            # Check if story details remain consistent over time
            # Legitimate stories maintain core facts
            # Misinformation often changes details

            time_since_creation = datetime.now(timezone.utc) - story.created_at.replace(
                tzinfo=timezone.utc
            )
            hours_since = time_since_creation.total_seconds() / 3600

            if hours_since < 1:
                return 0.6  # Too new to assess
            if hours_since < 24:
                return 0.8  # Recent, likely consistent
            return 0.9  # Mature story, proven consistent

        except Exception as e:
            logger.exception(f"Error analyzing temporal consistency: {e}")
            return None

    async def _analyze_content_quality(self, story: StoryResponse) -> float | None:
        """Analyze content quality indicators."""
        try:
            # Analyze text quality, completeness, source attribution
            # High-quality content tends to be more trustworthy

            content_length = len(story.description or "")

            if content_length < 50:
                return 0.4  # Very short content
            if content_length < 200:
                return 0.6  # Brief content
            if content_length < 1000:
                return 0.8  # Good length content
            return 0.9  # Comprehensive content

        except Exception as e:
            logger.exception(f"Error analyzing content quality: {e}")
            return None

    def _generate_signal_explanation(
        self, signal_type: str, value: float | None
    ) -> str:
        """Generate human-readable explanation for a trust signal."""
        if value is None:
            return f"{signal_type}: Insufficient data for analysis"

        value_percentage = round(value * 100, 1)

        explanations = {
            "source_credibility": (
                f"Source credibility: {value_percentage}% - "
                "Based on historical accuracy of sources"
            ),
            "velocity_pattern": (
                f"Velocity pattern: {value_percentage}% - "
                "Analysis of spread pattern authenticity"
            ),
            "cross_platform_correlation": (
                f"Cross-platform correlation: {value_percentage}% - "
                "Consistency across social platforms"
            ),
            "engagement_authenticity": (
                f"Engagement authenticity: {value_percentage}% - "
                "Bot detection and genuine interaction analysis"
            ),
            "temporal_consistency": (
                f"Temporal consistency: {value_percentage}% - "
                "Story stability over time"
            ),
            "content_quality": (
                f"Content quality: {value_percentage}% - "
                "Completeness and attribution assessment"
            ),
        }

        return explanations.get(signal_type, f"{signal_type}: {value_percentage}%")

    def _calculate_confidence(self, signals: dict[str, float | None]) -> float:
        """Calculate confidence level in the trust score."""
        available_signals = sum(1 for v in signals.values() if v is not None)
        total_signals = len(signals)

        # Confidence based on data availability
        data_confidence = available_signals / total_signals

        # Additional confidence factors could include:
        # - Data freshness
        # - Source diversity
        # - Sample size

        return min(1.0, data_confidence)

    async def detect_bots(self, posts: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Detect bot activity and coordinated campaigns in posts.

        Args:
            posts: List of social media posts to analyze

        Returns:
            Dict with bot detection results
        """
        try:
            if not posts:
                return {
                    "bot_probability": 0.0,
                    "coordinated_campaign": False,
                    "suspicious_accounts": [],
                    "analysis": "No posts provided for analysis",
                }

            # Analyze posting patterns
            account_stats = defaultdict(
                lambda: {
                    "post_count": 0,
                    "post_times": [],
                    "content_similarity": [],
                    "engagement_ratios": [],
                }
            )

            # Collect account statistics
            for post in posts:
                author = post.get("author", "unknown")
                account_stats[author]["post_count"] += 1

                if "created_at" in post:
                    account_stats[author]["post_times"].append(post["created_at"])

                # Analyze engagement patterns
                engagement = post.get("engagement", {})
                likes = engagement.get("likes", 0)
                retweets = engagement.get("retweets", 0)

                if retweets > 0:
                    ratio = likes / retweets
                    account_stats[author]["engagement_ratios"].append(ratio)

            # Detect suspicious patterns
            suspicious_accounts = []
            coordinated_indicators = 0

            for account, stats in account_stats.items():
                suspicion_score = 0.0

                # High posting frequency
                if stats["post_count"] > 10:
                    suspicion_score += 0.3

                # Unusual engagement ratios
                if stats["engagement_ratios"]:
                    avg_ratio = statistics.mean(stats["engagement_ratios"])
                    if avg_ratio < 0.1 or avg_ratio > 10:  # Unusual ratios
                        suspicion_score += 0.4

                # Timing analysis (placeholder)
                if len(stats["post_times"]) > 5:
                    # In production, analyze posting intervals for bot-like patterns
                    suspicion_score += 0.2

                if suspicion_score > 0.5:
                    suspicious_accounts.append(
                        {
                            "account": account,
                            "suspicion_score": suspicion_score,
                            "post_count": stats["post_count"],
                        }
                    )

            # Detect coordinated campaigns
            coordinated_campaign = len(suspicious_accounts) > 5
            if coordinated_campaign:
                coordinated_indicators += 1

            # Check for content similarity (placeholder)
            unique_content = {post.get("content", "")[:50] for post in posts}
            if len(unique_content) < len(posts) * 0.7:  # High similarity
                coordinated_indicators += 1

            # Calculate overall bot probability
            bot_probability = min(
                1.0, len(suspicious_accounts) / max(len(account_stats), 1)
            )

            # Boost probability for coordinated indicators
            if coordinated_indicators > 0:
                bot_probability = min(
                    1.0, bot_probability + 0.3 * coordinated_indicators
                )

            return {
                "bot_probability": round(bot_probability, 3),
                "coordinated_campaign": coordinated_campaign,
                "suspicious_accounts": suspicious_accounts[:10],  # Limit output
                "total_accounts_analyzed": len(account_stats),
                "coordinated_indicators": coordinated_indicators,
                "analysis": f"Analyzed {len(posts)} posts from {len(account_stats)} accounts",
            }

        except Exception as e:
            logger.exception(f"Error in bot detection: {e}")
            return {
                "bot_probability": 0.0,
                "coordinated_campaign": False,
                "suspicious_accounts": [],
                "analysis": f"Error in bot detection: {e!s}",
            }

    async def update_with_correlation(
        self, article: dict[str, Any], correlation: dict[str, Any]
    ) -> float:
        """
        Update trust score based on news correlation.

        Args:
            article: News article data
            correlation: Correlation analysis results

        Returns:
            Updated trust score
        """
        try:
            current_score = article.get("trust_score", 0.5)
            correlation_score = correlation.get("correlation_score", 0.0)

            # Positive correlation with mainstream news increases trust
            if correlation_score > 0.7:
                adjustment = 0.2  # Significant boost
            elif correlation_score > 0.5:
                adjustment = 0.1  # Moderate boost
            elif correlation_score > 0.3:
                adjustment = 0.05  # Small boost
            else:
                adjustment = -0.1  # Slight decrease for weak correlation

            updated_score = max(0.0, min(1.0, current_score + adjustment))

            logger.info(
                f"Updated trust score from {current_score} to {updated_score} "
                f"based on correlation score {correlation_score}"
            )

            return updated_score

        except Exception as e:
            logger.exception(f"Error updating trust score with correlation: {e}")
            return article.get("trust_score", 0.5)
