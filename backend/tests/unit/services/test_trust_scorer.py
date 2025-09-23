"""
Unit tests for TrustScorer service.

Tests the core trust scoring algorithms and bot detection functionality.
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from app.schemas.story import StoryResponse
from app.services.scoring.trust_scorer import TrustScorer


class TestTrustScorer:
    """Test cases for TrustScorer class."""

    @pytest.fixture
    def trust_scorer(self):
        """Create TrustScorer instance for testing."""
        return TrustScorer()

    @pytest.fixture
    def sample_story(self):
        """Create sample story for testing."""
        return StoryResponse(
            id=str(uuid.uuid4()),
            title="Sample News Story",
            description="This is a test story with some content for analysis",
            category="technology",
            trust_score=50.0,
            velocity=1.5,
            geographic_spread={"US": 40, "UK": 30, "CA": 20},
            first_seen_at=datetime.now(timezone.utc) - timedelta(hours=2),
            last_updated_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )

    @pytest.mark.asyncio
    async def test_calculate_score_basic(self, trust_scorer, sample_story):
        """Test basic trust score calculation."""
        result = await trust_scorer.calculate_score(sample_story)

        # Verify result structure
        assert "score" in result
        assert "score_percentage" in result
        assert "signals" in result
        assert "explanation" in result
        assert "calculated_at" in result
        assert "confidence" in result

        # Verify score range
        assert 0.0 <= result["score"] <= 1.0
        assert 0.0 <= result["score_percentage"] <= 100.0
        assert 0.0 <= result["confidence"] <= 1.0

        # Verify signals structure
        expected_signals = [
            "source_credibility",
            "velocity_pattern",
            "cross_platform_correlation",
            "engagement_authenticity",
            "temporal_consistency",
            "content_quality",
        ]
        for signal in expected_signals:
            assert signal in result["signals"]
            assert "value" in result["signals"][signal]
            assert "weight" in result["signals"][signal]
            assert "contribution" in result["signals"][signal]

    @pytest.mark.asyncio
    async def test_velocity_pattern_analysis(self, trust_scorer, sample_story):
        """Test velocity pattern analysis for different scenarios."""

        # Test slow organic spread
        sample_story.velocity = 0.05
        score = await trust_scorer._analyze_velocity_pattern(sample_story)
        assert score == 0.8

        # Test moderate viral spread
        sample_story.velocity = 0.5
        score = await trust_scorer._analyze_velocity_pattern(sample_story)
        assert score == 0.9

        # Test fast spread (possibly artificial)
        sample_story.velocity = 5.0
        score = await trust_scorer._analyze_velocity_pattern(sample_story)
        assert score == 0.6

        # Test very fast spread (likely artificial)
        sample_story.velocity = 20.0
        score = await trust_scorer._analyze_velocity_pattern(sample_story)
        assert score == 0.3

        # Test None velocity
        sample_story.velocity = None
        score = await trust_scorer._analyze_velocity_pattern(sample_story)
        assert score is None

    @pytest.mark.asyncio
    async def test_temporal_consistency_analysis(self, trust_scorer, sample_story):
        """Test temporal consistency analysis."""

        # Test very new story
        sample_story.created_at = datetime.now(timezone.utc) - timedelta(minutes=30)
        score = await trust_scorer._analyze_temporal_consistency(sample_story)
        assert score == 0.6

        # Test recent story
        sample_story.created_at = datetime.now(timezone.utc) - timedelta(hours=12)
        score = await trust_scorer._analyze_temporal_consistency(sample_story)
        assert score == 0.8

        # Test mature story
        sample_story.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        score = await trust_scorer._analyze_temporal_consistency(sample_story)
        assert score == 0.9

    @pytest.mark.asyncio
    async def test_content_quality_analysis(self, trust_scorer, sample_story):
        """Test content quality analysis based on description length."""

        # Test very short content
        sample_story.description = "Short"
        score = await trust_scorer._analyze_content_quality(sample_story)
        assert score == 0.4

        # Test brief content
        sample_story.description = "This is a brief description with some content but not too much detail here."
        score = await trust_scorer._analyze_content_quality(sample_story)
        assert score == 0.6

        # Test good length content
        sample_story.description = (
            "This is a comprehensive description with good detail. " * 5
        )
        score = await trust_scorer._analyze_content_quality(sample_story)
        assert score == 0.8

        # Test comprehensive content
        sample_story.description = (
            "This is a very comprehensive description with extensive detail. " * 20
        )
        score = await trust_scorer._analyze_content_quality(sample_story)
        assert score == 0.9

        # Test None description
        sample_story.description = None
        score = await trust_scorer._analyze_content_quality(sample_story)
        assert score == 0.4

    def test_generate_signal_explanation(self, trust_scorer):
        """Test signal explanation generation."""

        # Test with valid value
        explanation = trust_scorer._generate_signal_explanation(
            "source_credibility", 0.75
        )
        assert "Source credibility: 75.0%" in explanation
        assert "historical accuracy" in explanation

        # Test with None value
        explanation = trust_scorer._generate_signal_explanation(
            "velocity_pattern", None
        )
        assert "Insufficient data" in explanation

        # Test all signal types
        signal_types = [
            "source_credibility",
            "velocity_pattern",
            "cross_platform_correlation",
            "engagement_authenticity",
            "temporal_consistency",
            "content_quality",
        ]

        for signal_type in signal_types:
            explanation = trust_scorer._generate_signal_explanation(signal_type, 0.5)
            assert signal_type.replace("_", " ") in explanation.lower()
            assert "50.0%" in explanation

    def test_calculate_confidence(self, trust_scorer):
        """Test confidence calculation based on signal availability."""

        # Test with all signals available
        signals = {
            "source_credibility": 0.8,
            "velocity_pattern": 0.7,
            "cross_platform_correlation": 0.6,
            "engagement_authenticity": 0.9,
            "temporal_consistency": 0.8,
            "content_quality": 0.7,
        }
        confidence = trust_scorer._calculate_confidence(signals)
        assert confidence == 1.0

        # Test with some signals missing
        signals["velocity_pattern"] = None
        signals["cross_platform_correlation"] = None
        confidence = trust_scorer._calculate_confidence(signals)
        assert confidence == 4 / 6  # 4 available out of 6 total

        # Test with no signals
        signals = dict.fromkeys(signals.keys())
        confidence = trust_scorer._calculate_confidence(signals)
        assert confidence == 0.0


class TestBotDetection:
    """Test cases for bot detection functionality."""

    @pytest.fixture
    def trust_scorer(self):
        """Create TrustScorer instance for testing."""
        return TrustScorer()

    @pytest.fixture
    def organic_posts(self):
        """Create sample organic posts."""
        return [
            {
                "author": f"user_{i}",
                "content": f"This is a unique post about topic {i}",
                "engagement": {"likes": 10 + i, "retweets": 2 + i},
                "created_at": "2024-01-01T12:00:00Z",
            }
            for i in range(5)
        ]

    @pytest.fixture
    def bot_posts(self):
        """Create sample bot posts with suspicious patterns."""
        return [
            {
                "author": f"bot_user_{i}",
                "content": "Check this out! bit.ly/suspicious",
                "engagement": {"likes": 0, "retweets": 100},
                "created_at": "2024-01-01T12:00:00Z",
            }
            for i in range(15)
        ]

    @pytest.mark.asyncio
    async def test_detect_bots_empty_posts(self, trust_scorer):
        """Test bot detection with empty post list."""
        result = await trust_scorer.detect_bots([])

        assert result["bot_probability"] == 0.0
        assert result["coordinated_campaign"] is False
        assert result["suspicious_accounts"] == []
        assert "No posts provided" in result["analysis"]

    @pytest.mark.asyncio
    async def test_detect_bots_organic_content(self, trust_scorer, organic_posts):
        """Test bot detection with organic content."""
        result = await trust_scorer.detect_bots(organic_posts)

        assert result["bot_probability"] < 0.5
        assert result["coordinated_campaign"] is False
        assert len(result["suspicious_accounts"]) == 0
        assert result["total_accounts_analyzed"] == 5

    @pytest.mark.asyncio
    async def test_detect_bots_suspicious_content(self, trust_scorer, bot_posts):
        """Test bot detection with suspicious bot-like content."""
        result = await trust_scorer.detect_bots(bot_posts)

        assert result["bot_probability"] > 0.7
        assert result["coordinated_campaign"] is True
        assert len(result["suspicious_accounts"]) > 5
        assert result["total_accounts_analyzed"] == 15

    @pytest.mark.asyncio
    async def test_detect_bots_mixed_content(
        self, trust_scorer, organic_posts, bot_posts
    ):
        """Test bot detection with mixed organic and bot content."""
        mixed_posts = organic_posts + bot_posts
        result = await trust_scorer.detect_bots(mixed_posts)

        assert 0.3 < result["bot_probability"] < 0.9
        assert result["total_accounts_analyzed"] == 20
        assert len(result["suspicious_accounts"]) > 0

    @pytest.mark.asyncio
    async def test_detect_bots_engagement_analysis(self, trust_scorer):
        """Test bot detection based on engagement patterns."""
        posts_with_unusual_engagement = [
            {
                "author": f"suspicious_{i}",
                "content": f"Post {i}",
                "engagement": {"likes": 1, "retweets": 1000},  # Unusual ratio
                "created_at": "2024-01-01T12:00:00Z",
            }
            for i in range(10)
        ]

        result = await trust_scorer.detect_bots(posts_with_unusual_engagement)

        # Should detect unusual engagement patterns
        assert result["bot_probability"] > 0.5
        assert len(result["suspicious_accounts"]) > 0

        # Check if accounts are flagged for unusual engagement
        for account in result["suspicious_accounts"]:
            assert account["suspicion_score"] > 0.5

    @pytest.mark.asyncio
    async def test_detect_bots_high_frequency_posting(self, trust_scorer):
        """Test bot detection based on posting frequency."""
        high_frequency_posts = [
            {
                "author": "spam_bot",
                "content": f"Automated post {i}",
                "engagement": {"likes": 5, "retweets": 1},
                "created_at": "2024-01-01T12:00:00Z",
            }
            for i in range(25)  # Very high post count for single account
        ]

        result = await trust_scorer.detect_bots(high_frequency_posts)

        assert result["bot_probability"] > 0.6
        assert len(result["suspicious_accounts"]) > 0

        # The high-frequency account should be flagged
        spam_account = next(
            (
                acc
                for acc in result["suspicious_accounts"]
                if acc["account"] == "spam_bot"
            ),
            None,
        )
        assert spam_account is not None
        assert spam_account["post_count"] == 25


class TestTrustScoreCorrelation:
    """Test cases for trust score correlation with news."""

    @pytest.fixture
    def trust_scorer(self):
        """Create TrustScorer instance for testing."""
        return TrustScorer()

    @pytest.mark.asyncio
    async def test_update_with_strong_correlation(self, trust_scorer):
        """Test trust score update with strong news correlation."""
        article = {"trust_score": 0.5}
        correlation = {"correlation_score": 0.8}

        updated_score = await trust_scorer.update_with_correlation(article, correlation)

        assert updated_score > 0.5  # Should increase
        assert updated_score <= 1.0  # Should not exceed maximum

    @pytest.mark.asyncio
    async def test_update_with_moderate_correlation(self, trust_scorer):
        """Test trust score update with moderate news correlation."""
        article = {"trust_score": 0.5}
        correlation = {"correlation_score": 0.6}

        updated_score = await trust_scorer.update_with_correlation(article, correlation)

        assert updated_score > 0.5  # Should increase slightly
        assert updated_score < 0.7  # Should not increase too much

    @pytest.mark.asyncio
    async def test_update_with_weak_correlation(self, trust_scorer):
        """Test trust score update with weak news correlation."""
        article = {"trust_score": 0.5}
        correlation = {"correlation_score": 0.2}

        updated_score = await trust_scorer.update_with_correlation(article, correlation)

        assert updated_score < 0.5  # Should decrease
        assert updated_score >= 0.0  # Should not go below minimum

    @pytest.mark.asyncio
    async def test_update_with_no_correlation(self, trust_scorer):
        """Test trust score update with no correlation data."""
        article = {"trust_score": 0.5}
        correlation = {}

        updated_score = await trust_scorer.update_with_correlation(article, correlation)

        assert updated_score < 0.5  # Should decrease due to default 0.0 correlation

    @pytest.mark.asyncio
    async def test_update_with_missing_trust_score(self, trust_scorer):
        """Test trust score update when article has no trust score."""
        article = {}
        correlation = {"correlation_score": 0.7}

        updated_score = await trust_scorer.update_with_correlation(article, correlation)

        assert updated_score > 0.5  # Should start from default 0.5 and increase

    @pytest.mark.asyncio
    async def test_update_score_clamping(self, trust_scorer):
        """Test that updated scores are properly clamped to [0, 1] range."""

        # Test upper bound clamping
        article = {"trust_score": 0.95}
        correlation = {"correlation_score": 0.9}
        updated_score = await trust_scorer.update_with_correlation(article, correlation)
        assert updated_score <= 1.0

        # Test lower bound clamping
        article = {"trust_score": 0.05}
        correlation = {"correlation_score": 0.1}
        updated_score = await trust_scorer.update_with_correlation(article, correlation)
        assert updated_score >= 0.0


class TestTrustScorerErrorHandling:
    """Test error handling in TrustScorer."""

    @pytest.fixture
    def trust_scorer(self):
        """Create TrustScorer instance for testing."""
        return TrustScorer()

    @pytest.mark.asyncio
    async def test_calculate_score_with_invalid_story(self, trust_scorer):
        """Test trust score calculation with invalid story data."""
        # Test with story that might cause errors
        invalid_story = Mock()
        invalid_story.id = str(uuid.uuid4())
        invalid_story.description = None
        invalid_story.velocity = None
        invalid_story.created_at = None

        result = await trust_scorer.calculate_score(invalid_story)

        # Should return default error response
        assert result["score"] == 0.5
        assert result["score_percentage"] == 50.0
        assert result["confidence"] == 0.0
        assert "Error calculating trust score" in result["explanation"]

    @pytest.mark.asyncio
    async def test_bot_detection_error_handling(self, trust_scorer):
        """Test bot detection error handling."""
        # Test with malformed posts
        malformed_posts = [{"invalid": "data"}, None, {"author": None, "content": None}]

        result = await trust_scorer.detect_bots(malformed_posts)

        # Should handle errors gracefully
        assert "bot_probability" in result
        assert "analysis" in result
        assert result["bot_probability"] >= 0.0

    @pytest.mark.asyncio
    async def test_correlation_update_error_handling(self, trust_scorer):
        """Test error handling in correlation updates."""

        # Test with invalid data
        result = await trust_scorer.update_with_correlation(None, None)
        assert result == 0.5  # Default fallback

        # Test with malformed data
        result = await trust_scorer.update_with_correlation(
            {"invalid": "data"}, {"invalid": "correlation"}
        )
        assert 0.0 <= result <= 1.0  # Should return valid score
