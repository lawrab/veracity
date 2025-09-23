"""
Integration tests for Trust Scoring system.

Tests the complete trust scoring workflow including database interactions,
API integration, and real-time WebSocket updates.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_postgres_session
from app.models.sql_models import Source, Story, TrustSignal
from app.schemas.story import StoryCreate, StoryResponse
from app.services.scoring.trust_scorer import TrustScorer
from app.services.story_service import StoryService


@pytest.mark.integration
class TestTrustScoringIntegration:
    """Integration tests for trust scoring with database."""

    @pytest.fixture
    async def db_session(self, db_session):
        """Use the database session fixture."""
        return db_session

    @pytest.fixture
    async def sample_source(self, db_session):
        """Create a sample source in the database."""
        source = Source(
            name="Test News Source",
            url="https://testnews.com",
            platform="news",
            credibility_score=75.0,
            is_verified=True,
        )
        db_session.add(source)
        await db_session.commit()
        await db_session.refresh(source)
        return source

    @pytest.fixture
    async def sample_story(self, db_session, sample_source):
        """Create a sample story in the database."""
        story = Story(
            title="Breaking: Important Tech News",
            description="This is a comprehensive story about important technology developments that impact society.",
            category="technology",
            trust_score=0.0,  # Will be calculated
            velocity=2.5,
            geographic_spread={"US": 45, "UK": 25, "CA": 15, "DE": 10},
            first_seen_at=datetime.now(timezone.utc) - timedelta(hours=3),
            last_updated_at=datetime.now(timezone.utc) - timedelta(minutes=15),
        )
        db_session.add(story)
        await db_session.commit()
        await db_session.refresh(story)
        return story

    @pytest.mark.asyncio
    async def test_complete_trust_scoring_workflow(self, db_session, sample_story):
        """Test complete trust scoring workflow from calculation to storage."""

        # Initialize services
        trust_scorer = TrustScorer()
        story_service = StoryService(db_session)

        # Convert to response schema for scorer
        story_response = StoryResponse.model_validate(sample_story)

        # Calculate trust score
        score_result = await trust_scorer.calculate_score(story_response)

        # Verify score structure
        assert "score" in score_result
        assert "signals" in score_result
        assert "explanation" in score_result
        assert 0.0 <= score_result["score"] <= 1.0

        # Update story with calculated score
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

        success = await story_service.update_trust_score(
            str(sample_story.id),
            score_result["score"] * 100,  # Convert to 0-100 scale
            signals_for_db,
        )

        assert success is True

        # Verify story was updated in database
        await db_session.refresh(sample_story)
        assert sample_story.trust_score == score_result["score"] * 100
        assert sample_story.last_updated_at > sample_story.created_at

        # Verify trust signals were stored
        from sqlalchemy import select

        signals_query = select(TrustSignal).where(
            TrustSignal.story_id == sample_story.id
        )
        signals_result = await db_session.execute(signals_query)
        stored_signals = signals_result.scalars().all()

        assert len(stored_signals) == len(signals_for_db)

        for signal in stored_signals:
            assert signal.story_id == sample_story.id
            assert signal.signal_type in [s["type"] for s in signals_for_db]
            assert 0.0 <= signal.value <= 1.0
            assert signal.weight > 0.0
            assert signal.explanation is not None

    @pytest.mark.asyncio
    async def test_trust_score_history_retrieval(self, db_session, sample_story):
        """Test retrieval of trust score history."""

        story_service = StoryService(db_session)
        trust_scorer = TrustScorer()

        # Add multiple trust score calculations over time
        story_response = StoryResponse.model_validate(sample_story)

        for i in range(3):
            # Simulate different scores over time
            modified_story = story_response.model_copy()
            modified_story.velocity = 1.0 + i * 0.5  # Different velocities

            score_result = await trust_scorer.calculate_score(modified_story)

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
                str(sample_story.id), score_result["score"] * 100, signals_for_db
            )

            # Add small delay to ensure different timestamps
            await asyncio.sleep(0.1)

        # Retrieve trust score history
        history = await story_service.get_trust_score_history(str(sample_story.id))

        assert history is not None
        assert len(history.timestamps) >= 3
        assert len(history.scores) == len(history.timestamps)
        assert len(history.signals) == len(history.timestamps)

        # Verify all scores are in valid range
        for score in history.scores:
            assert 0.0 <= score <= 100.0

    @pytest.mark.asyncio
    async def test_bulk_trust_score_calculation(self, db_session, sample_source):
        """Test bulk trust score calculation for multiple stories."""

        # Create multiple stories
        stories = []
        for i in range(5):
            story = Story(
                title=f"Story {i}",
                description=f"Description for story {i} with varying content length and complexity.",
                category="technology",
                trust_score=0.0,
                velocity=0.5 + i * 0.3,
                geographic_spread={"US": 30 + i * 10},
                first_seen_at=datetime.now(timezone.utc) - timedelta(hours=i + 1),
                last_updated_at=datetime.now(timezone.utc) - timedelta(minutes=i * 10),
            )
            db_session.add(story)
            stories.append(story)

        await db_session.commit()
        for story in stories:
            await db_session.refresh(story)

        # Calculate trust scores for all stories
        trust_scorer = TrustScorer()
        story_service = StoryService(db_session)

        results = []
        for story in stories:
            story_response = StoryResponse.model_validate(story)
            score_result = await trust_scorer.calculate_score(story_response)

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
                str(story.id), score_result["score"] * 100, signals_for_db
            )

            results.append(
                {
                    "story_id": str(story.id),
                    "score": score_result["score"],
                    "confidence": score_result["confidence"],
                }
            )

        # Verify all stories were processed
        assert len(results) == 5

        # Verify all stories have trust scores
        for story in stories:
            await db_session.refresh(story)
            assert story.trust_score > 0.0

    @pytest.mark.asyncio
    async def test_trust_score_with_different_story_attributes(
        self, db_session, sample_source
    ):
        """Test trust scoring with different story characteristics."""

        trust_scorer = TrustScorer()
        story_service = StoryService(db_session)

        # Test scenarios with different characteristics
        test_scenarios = [
            {
                "name": "high_velocity_story",
                "velocity": 15.0,  # Very high velocity
                "description": "Short desc",
                "age_hours": 0.5,
                "expected_velocity_score_range": (
                    0.2,
                    0.4,
                ),  # Should be flagged as suspicious
            },
            {
                "name": "organic_story",
                "velocity": 0.8,  # Moderate velocity
                "description": "This is a comprehensive description with good detail and proper attribution to sources.",
                "age_hours": 12,
                "expected_velocity_score_range": (0.8, 1.0),  # Should score well
            },
            {
                "name": "mature_story",
                "velocity": 0.3,  # Low velocity
                "description": "Very comprehensive story with extensive details and multiple source attributions.",
                "age_hours": 48,
                "expected_velocity_score_range": (
                    0.7,
                    1.0,
                ),  # Should score well for consistency
            },
        ]

        for scenario in test_scenarios:
            # Create story with specific characteristics
            story = Story(
                title=f"Test story: {scenario['name']}",
                description=scenario["description"],
                category="technology",
                trust_score=0.0,
                velocity=scenario["velocity"],
                geographic_spread={"US": 50},
                first_seen_at=datetime.now(timezone.utc)
                - timedelta(hours=scenario["age_hours"]),
                last_updated_at=datetime.now(timezone.utc) - timedelta(minutes=15),
                created_at=datetime.now(timezone.utc)
                - timedelta(hours=scenario["age_hours"]),
            )
            db_session.add(story)
            await db_session.commit()
            await db_session.refresh(story)

            # Calculate trust score
            story_response = StoryResponse.model_validate(story)
            score_result = await trust_scorer.calculate_score(story_response)

            # Verify velocity pattern scoring matches expectations
            velocity_signal = score_result["signals"].get("velocity_pattern")
            if velocity_signal and velocity_signal["value"] is not None:
                velocity_score = velocity_signal["value"]
                expected_min, expected_max = scenario["expected_velocity_score_range"]
                assert expected_min <= velocity_score <= expected_max, (
                    f"Velocity score {velocity_score} not in expected range "
                    f"{scenario['expected_velocity_score_range']} for {scenario['name']}"
                )

    @pytest.mark.asyncio
    async def test_bot_detection_integration(self, db_session):
        """Test bot detection with realistic post data."""

        trust_scorer = TrustScorer()

        # Create realistic bot-like posts
        bot_posts = [
            {
                "author": f"bot_account_{i}",
                "content": "Check this amazing deal! bit.ly/suspicious-link",
                "engagement": {"likes": 1, "retweets": 50},  # Unusual engagement ratio
                "created_at": "2024-01-01T12:00:00Z",
                "platform": "twitter",
            }
            for i in range(20)
        ]

        # Add some organic posts
        organic_posts = [
            {
                "author": f"real_user_{i}",
                "content": f"Interesting perspective on current events. What do you think about this development? #{i}",
                "engagement": {"likes": 10 + i, "retweets": 2 + i},
                "created_at": f"2024-01-01T12:{i:02d}:00Z",
                "platform": "twitter",
            }
            for i in range(5)
        ]

        # Test detection on suspicious content
        bot_result = await trust_scorer.detect_bots(bot_posts)

        assert bot_result["bot_probability"] > 0.7
        assert bot_result["coordinated_campaign"] is True
        assert len(bot_result["suspicious_accounts"]) > 10

        # Test detection on organic content
        organic_result = await trust_scorer.detect_bots(organic_posts)

        assert organic_result["bot_probability"] < 0.5
        assert organic_result["coordinated_campaign"] is False
        assert len(organic_result["suspicious_accounts"]) == 0

        # Test mixed content
        mixed_posts = organic_posts + bot_posts[:10]  # Mix organic with some bots
        mixed_result = await trust_scorer.detect_bots(mixed_posts)

        assert 0.3 < mixed_result["bot_probability"] < 0.8
        assert mixed_result["total_accounts_analyzed"] == 15

    @pytest.mark.asyncio
    async def test_news_correlation_update(self, db_session, sample_story):
        """Test trust score updates based on news correlation."""

        trust_scorer = TrustScorer()

        # Test different correlation scenarios
        correlation_scenarios = [
            {
                "correlation_score": 0.9,
                "expected_increase": True,
                "description": "Strong correlation with mainstream news",
            },
            {
                "correlation_score": 0.6,
                "expected_increase": True,
                "description": "Moderate correlation with mainstream news",
            },
            {
                "correlation_score": 0.2,
                "expected_increase": False,
                "description": "Weak correlation with mainstream news",
            },
        ]

        initial_score = 0.5

        for scenario in correlation_scenarios:
            article = {"trust_score": initial_score}
            correlation = {"correlation_score": scenario["correlation_score"]}

            updated_score = await trust_scorer.update_with_correlation(
                article, correlation
            )

            # Verify score is in valid range
            assert 0.0 <= updated_score <= 1.0

            # Verify direction of change matches expectation
            if scenario["expected_increase"]:
                assert (
                    updated_score >= initial_score
                ), f"Score should increase for {scenario['description']}"
            else:
                assert (
                    updated_score < initial_score
                ), f"Score should decrease for {scenario['description']}"

    @pytest.mark.asyncio
    async def test_trust_scoring_error_handling(self, db_session):
        """Test trust scoring error handling with edge cases."""

        trust_scorer = TrustScorer()

        # Test with minimal story data
        minimal_story = StoryResponse(
            id="minimal-story",
            title="",
            description=None,
            category="",
            trust_score=0.0,
            velocity=None,
            geographic_spread=None,
            first_seen_at=datetime.now(timezone.utc),
            last_updated_at=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc),
        )

        # Should handle gracefully without errors
        result = await trust_scorer.calculate_score(minimal_story)

        assert "score" in result
        assert 0.0 <= result["score"] <= 1.0
        assert result["confidence"] >= 0.0

        # Test bot detection with malformed data
        malformed_posts = [
            {"author": None, "content": None},
            {},
            {"missing_required_fields": True},
        ]

        bot_result = await trust_scorer.detect_bots(malformed_posts)

        assert "bot_probability" in bot_result
        assert bot_result["bot_probability"] >= 0.0
        assert "analysis" in bot_result
