"""End-to-end tests for complete workflows."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.services.ingestion.reddit_collector import RedditCollector
from app.services.ingestion.twitter_collector import TwitterCollector
from app.services.processing.nlp_processor import NLPProcessor
from app.services.scoring.trust_scorer import TrustScorer
from app.services.story_service import StoryService
from app.services.trend_service import TrendService


@pytest.mark.e2e
class TestCompleteWorkflow:
    """End-to-end tests for complete data processing workflows."""

    @pytest.fixture
    async def setup_services(self, db_session, mongodb_client):
        """Setup all required services for E2E tests."""
        services = {
            "reddit_collector": RedditCollector(),
            "twitter_collector": TwitterCollector(),
            "nlp_processor": NLPProcessor(),
            "trend_service": TrendService(db_session),
            "story_service": StoryService(db_session),
            "trust_scorer": TrustScorer(),
        }

        # Initialize collectors with MongoDB
        services["reddit_collector"].mongodb = mongodb_client
        services["twitter_collector"].mongodb = mongodb_client

        return services

    @pytest.mark.slow
    async def test_complete_data_pipeline(self, setup_services, sample_social_post):
        """Test complete data pipeline from ingestion to scoring."""
        services = setup_services

        # Step 1: Collect social media data
        with patch.object(
            services["reddit_collector"], "collect_trending_posts"
        ) as mock_reddit:
            mock_reddit.return_value = [sample_social_post]

            posts = await services["reddit_collector"].collect_trending_posts(
                subreddits=["technology"], limit=10
            )

            assert len(posts) > 0

        # Step 2: Process posts with NLP
        processed_posts = await services["nlp_processor"].process_posts(posts)
        assert all("entities" in p for p in processed_posts)
        assert all("sentiment" in p for p in processed_posts)

        # Step 3: Detect trends
        trends = await services["trend_service"].detect_trends(processed_posts)
        assert len(trends) > 0

        # Step 4: Create story from trend
        story_data = {
            "title": trends[0]["name"],
            "content": f"Trending topic: {trends[0]['keywords']}",
            "source": "Reddit",
            "trend_id": trends[0].get("id"),
        }
        story = await services["story_service"].create_story(story_data)
        assert story.id is not None

        # Step 5: Calculate trust score
        trust_score = await services["trust_scorer"].calculate_score(story)
        assert 0 <= trust_score["score"] <= 1
        assert "signals" in trust_score
        assert "explanation" in trust_score

    @pytest.mark.slow
    async def test_real_time_monitoring_workflow(self, setup_services):
        """Test real-time monitoring and alerting workflow."""
        services = setup_services

        # Simulate real-time monitoring
        monitoring_task = asyncio.create_task(
            services["trend_service"].monitor_trends_realtime()
        )

        # Wait for initial data
        await asyncio.sleep(2)

        # Inject spike in activity
        spike_posts = [
            {
                "platform": "twitter",
                "content": "BREAKING: Major announcement #breaking",
                "engagement": {"likes": 10000, "retweets": 5000},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            for _ in range(50)
        ]

        # Process spike
        alerts = await services["trend_service"].detect_anomalies(spike_posts)
        assert len(alerts) > 0
        assert alerts[0]["type"] == "spike"

        monitoring_task.cancel()

    @pytest.mark.slow
    async def test_cross_platform_correlation(self, setup_services):
        """Test correlation of trends across multiple platforms."""
        services = setup_services

        # Collect from multiple platforms
        reddit_posts = [
            {
                "platform": "reddit",
                "content": "AI breakthrough announced today",
                "metadata": {"subreddit": "technology"},
            }
        ]

        twitter_posts = [
            {
                "platform": "twitter",
                "content": "Amazing AI breakthrough! #AI #Tech",
                "metadata": {"hashtags": ["AI", "Tech"]},
            }
        ]

        # Detect trends from both platforms
        all_posts = reddit_posts + twitter_posts
        trends = await services["trend_service"].detect_trends(all_posts)

        # Find cross-platform trends
        cross_platform = [
            t for t in trends if len({p["platform"] for p in t.get("posts", [])}) > 1
        ]

        assert len(cross_platform) > 0

    @pytest.mark.slow
    async def test_bot_detection_workflow(self, setup_services):
        """Test bot detection in data pipeline."""
        services = setup_services

        # Create suspicious posts pattern
        bot_posts = [
            {
                "platform": "twitter",
                "author": f"bot_user_{i}",
                "content": "Check this out! bit.ly/fake",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "engagement": {"likes": 0, "retweets": 100},
            }
            for i in range(20)
        ]

        # Run bot detection
        bot_analysis = await services["trust_scorer"].detect_bots(bot_posts)

        assert bot_analysis["bot_probability"] > 0.7
        assert bot_analysis["coordinated_campaign"] is True
        assert len(bot_analysis["suspicious_accounts"]) >= 10

    @pytest.mark.slow
    async def test_news_correlation_workflow(self, setup_services, sample_news_article):
        """Test correlation between social trends and news articles."""
        services = setup_services

        # Create trend
        trend = {
            "name": "AI Technology",
            "keywords": ["AI", "technology", "innovation"],
            "platform": "twitter",
        }

        # Find correlated news
        correlations = await services["story_service"].find_correlated_news(
            trend, [sample_news_article]
        )

        assert len(correlations) > 0
        assert correlations[0]["correlation_score"] > 0.5

        # Update trust score based on correlation
        updated_score = await services["trust_scorer"].update_with_correlation(
            sample_news_article, correlations[0]
        )

        assert updated_score != sample_news_article.get("trust_score", 0.5)
