"""Unit tests for TrendService."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trend import Trend
from app.schemas.trend import TrendCreate
from app.services.trend_service import TrendService


class TestTrendService:
    """Test cases for TrendService."""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session."""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def trend_service(self, mock_db_session):
        """Create TrendService instance with mock session."""
        return TrendService(mock_db_session)

    @pytest.fixture
    def sample_posts(self):
        """Sample social media posts for testing."""
        return [
            {
                "platform": "twitter",
                "content": "AI is revolutionizing healthcare #AI #HealthTech",
                "engagement": {"likes": 1000, "retweets": 500},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "platform": "reddit",
                "content": "New AI model beats human performance",
                "engagement": {"upvotes": 2000, "comments": 300},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "platform": "twitter",
                "content": "Healthcare AI saves lives #AI #Healthcare",
                "engagement": {"likes": 800, "retweets": 400},
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

    @pytest.mark.unit
    async def test_detect_trends_identifies_clusters(self, trend_service, sample_posts):
        """Test that detect_trends correctly identifies topic clusters."""
        with patch(
            "app.services.trend_service.TrendService._extract_topics"
        ) as mock_extract:
            mock_extract.return_value = ["AI", "healthcare", "technology"]

            with patch(
                "app.services.trend_service.TrendService._calculate_trend_score"
            ) as mock_score:
                mock_score.return_value = 0.85

                trends = await trend_service.detect_trends(sample_posts)

                assert len(trends) > 0
                assert all(isinstance(t, dict) for t in trends)
                mock_extract.assert_called()
                mock_score.assert_called()

    @pytest.mark.unit
    async def test_calculate_trend_score(self, trend_service):
        """Test trend score calculation logic."""
        cluster = {
            "posts": [
                {"engagement": {"likes": 1000, "comments": 100}},
                {"engagement": {"upvotes": 2000, "comments": 200}},
            ],
            "growth_rate": 0.5,
            "platforms": ["twitter", "reddit"],
        }

        score = await trend_service._calculate_trend_score(cluster)

        assert 0 <= score <= 1
        assert isinstance(score, float)

    @pytest.mark.unit
    async def test_create_trend(self, trend_service, mock_db_session):
        """Test creating a new trend in database."""
        trend_data = TrendCreate(
            name="AI Healthcare Revolution",
            keywords=["AI", "healthcare", "technology"],
            score=0.85,
            platform="twitter",
            post_count=150,
        )

        mock_trend = Trend(**trend_data.model_dump())
        mock_trend.id = 1

        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.refresh = AsyncMock()

        result = await trend_service.create_trend(trend_data)

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.unit
    async def test_get_trending_topics(self, trend_service, mock_db_session):
        """Test retrieving trending topics."""
        mock_trends = [
            MagicMock(name="AI", score=0.9, post_count=1000),
            MagicMock(name="Healthcare", score=0.85, post_count=800),
        ]

        mock_query = AsyncMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = mock_trends

        mock_db_session.query = MagicMock(return_value=mock_query)

        trends = await trend_service.get_trending_topics(limit=10)

        assert len(trends) == 2
        assert trends[0].score >= trends[1].score

    @pytest.mark.unit
    async def test_update_trend_score(self, trend_service, mock_db_session):
        """Test updating trend score based on new data."""
        trend_id = 1
        new_posts = [{"engagement": {"likes": 500}}, {"engagement": {"likes": 600}}]

        mock_trend = MagicMock(id=trend_id, score=0.7, post_count=100)
        mock_db_session.get = AsyncMock(return_value=mock_trend)
        mock_db_session.commit = AsyncMock()

        updated_trend = await trend_service.update_trend_score(trend_id, new_posts)

        assert updated_trend.score != 0.7
        assert updated_trend.post_count > 100
        mock_db_session.commit.assert_called_once()

    @pytest.mark.unit
    async def test_identify_emerging_trends(self, trend_service, sample_posts):
        """Test identification of emerging trends with high growth rate."""
        with patch(
            "app.services.trend_service.TrendService._calculate_growth_rate"
        ) as mock_growth:
            mock_growth.return_value = 2.5  # 250% growth

            emerging = await trend_service.identify_emerging_trends(sample_posts)

            assert len(emerging) > 0
            assert all(t.get("growth_rate", 0) > 1 for t in emerging)

    @pytest.mark.unit
    async def test_correlate_with_news(self, trend_service):
        """Test correlation between trends and news articles."""
        trend = {"keywords": ["AI", "healthcare"]}
        news_articles = [
            {
                "title": "AI transforms healthcare industry",
                "categories": ["technology", "health"],
            },
            {"title": "Sports news update", "categories": ["sports"]},
        ]

        correlations = await trend_service.correlate_with_news(trend, news_articles)

        assert len(correlations) == 1
        assert "AI" in correlations[0]["title"]
