"""
Unit tests for Trust Scoring API endpoints.

Tests the REST API functionality for trust score calculations,
bot detection, and trust score management.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.story import StoryResponse


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def test_story_id():
    """Generate a test story UUID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_story_response(test_story_id):
    """Create sample story response."""
    return StoryResponse(
        id=test_story_id,
        title="Test Story",
        description="Test description",
        category="technology",
        trust_score=75.0,
        velocity=1.2,
        geographic_spread={"US": 50},
        first_seen_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_trust_score_result():
    """Create mock trust score calculation result."""
    return {
        "score": 0.75,
        "score_percentage": 75.0,
        "signals": {
            "source_credibility": {
                "value": 0.8,
                "weight": 0.25,
                "contribution": 0.2,
            },
            "velocity_pattern": {
                "value": 0.7,
                "weight": 0.20,
                "contribution": 0.14,
            },
        },
        "explanation": ["Source credibility: 80.0%", "Velocity pattern: 70.0%"],
        "calculated_at": "2024-01-01T12:00:00Z",
        "confidence": 0.9,
    }


class TestTrustAPI:
    """Test cases for Trust API endpoints."""


class TestCalculateTrustScore:
    """Test /trust/calculate endpoint."""

    @patch("app.api.v1.endpoints.trust.StoryService")
    @patch("app.api.v1.endpoints.trust.TrustScorer")
    @patch("app.api.v1.endpoints.trust.websocket_manager")
    def test_calculate_trust_score_success(
        self,
        mock_websocket,
        mock_trust_scorer_class,
        mock_story_service_class,
        client,
        test_story_id,
        sample_story_response,
        mock_trust_score_result,
    ):
        """Test successful trust score calculation."""

        # Setup mocks
        mock_story_service = AsyncMock()
        mock_story_service.get_story_by_id.return_value = sample_story_response
        mock_story_service.update_trust_score.return_value = True
        mock_story_service_class.return_value = mock_story_service

        mock_trust_scorer = AsyncMock()
        mock_trust_scorer.calculate_score.return_value = mock_trust_score_result
        mock_trust_scorer_class.return_value = mock_trust_scorer

        mock_websocket.broadcast_trust_score_update = AsyncMock()

        # Make request
        response = client.post(
            "/api/v1/trust/calculate", json={"story_id": test_story_id}
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["score"] == 0.75
        assert data["score_percentage"] == 75.0
        assert "signals" in data
        assert "explanation" in data
        assert data["confidence"] == 0.9

        # Verify service calls
        mock_story_service.get_story_by_id.assert_called_once_with(test_story_id)
        mock_trust_scorer.calculate_score.assert_called_once_with(sample_story_response)
        mock_story_service.update_trust_score.assert_called_once()
        mock_websocket.broadcast_trust_score_update.assert_called_once()

    @patch("app.api.v1.endpoints.trust.StoryService")
    def test_calculate_trust_score_story_not_found(
        self, mock_story_service_class, client
    ):
        """Test trust score calculation when story is not found."""

        mock_story_service = AsyncMock()
        mock_story_service.get_story_by_id.return_value = None
        mock_story_service_class.return_value = mock_story_service

        response = client.post(
            "/api/v1/trust/calculate", json={"story_id": "nonexistent-story"}
        )

        assert response.status_code == 404
        assert "Story not found" in response.json()["detail"]

    def test_calculate_trust_score_invalid_request(self, client):
        """Test trust score calculation with invalid request data."""

        # Missing story_id
        response = client.post("/api/v1/trust/calculate", json={})
        assert response.status_code == 422

        # Invalid story_id type
        response = client.post("/api/v1/trust/calculate", json={"story_id": 123})
        assert response.status_code == 422


class TestBotDetection:
    """Test /trust/bot-detection endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def sample_posts(self):
        """Sample posts for bot detection."""
        return [
            {
                "author": "user1",
                "content": "Interesting news today!",
                "engagement": {"likes": 10, "retweets": 2},
                "created_at": "2024-01-01T12:00:00Z",
            },
            {
                "author": "user2",
                "content": "Another perspective on this topic",
                "engagement": {"likes": 5, "retweets": 1},
                "created_at": "2024-01-01T12:05:00Z",
            },
        ]

    @patch("app.api.v1.endpoints.trust.TrustScorer")
    def test_bot_detection_success(self, mock_trust_scorer_class, client, sample_posts):
        """Test successful bot detection."""

        mock_detection_result = {
            "bot_probability": 0.3,
            "coordinated_campaign": False,
            "suspicious_accounts": [],
            "total_accounts_analyzed": 2,
            "analysis": "Analyzed 2 posts from 2 accounts",
        }

        mock_trust_scorer = AsyncMock()
        mock_trust_scorer.detect_bots.return_value = mock_detection_result
        mock_trust_scorer_class.return_value = mock_trust_scorer

        response = client.post(
            "/api/v1/trust/bot-detection", json={"posts": sample_posts}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["bot_probability"] == 0.3
        assert data["coordinated_campaign"] is False
        assert data["total_accounts_analyzed"] == 2
        assert "analysis" in data

    def test_bot_detection_empty_posts(self, client):
        """Test bot detection with empty posts list."""

        response = client.post("/api/v1/trust/bot-detection", json={"posts": []})

        assert response.status_code == 400
        assert "No posts provided" in response.json()["detail"]

    def test_bot_detection_too_many_posts(self, client):
        """Test bot detection with too many posts."""

        large_posts_list = [
            {"author": f"user{i}", "content": f"post {i}"} for i in range(1001)
        ]

        response = client.post(
            "/api/v1/trust/bot-detection", json={"posts": large_posts_list}
        )

        assert response.status_code == 400
        assert "Too many posts" in response.json()["detail"]


class TestGetCurrentTrustScore:
    """Test /trust/story/{story_id}/score endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @patch("app.api.v1.endpoints.trust.StoryService")
    def test_get_current_score_success(
        self, mock_story_service_class, client, test_story_id, sample_story_response
    ):
        """Test getting current trust score."""

        mock_story_service = AsyncMock()
        mock_story_service.get_story_by_id.return_value = sample_story_response
        mock_story_service_class.return_value = mock_story_service

        response = client.get(f"/api/v1/trust/story/{test_story_id}/score")

        assert response.status_code == 200
        data = response.json()

        assert data["score"] == 0.75  # 75.0 / 100
        assert data["score_percentage"] == 75.0
        assert "explanation" in data

    @patch("app.api.v1.endpoints.trust.StoryService")
    @patch("app.api.v1.endpoints.trust.TrustScorer")
    def test_get_current_score_recalculate(
        self,
        mock_trust_scorer_class,
        mock_story_service_class,
        client,
        test_story_id,
        sample_story_response,
        mock_trust_score_result,
    ):
        """Test getting trust score with recalculation."""

        mock_story_service = AsyncMock()
        mock_story_service.get_story_by_id.return_value = sample_story_response
        mock_story_service.update_trust_score.return_value = True
        mock_story_service_class.return_value = mock_story_service

        mock_trust_scorer = AsyncMock()
        mock_trust_scorer.calculate_score.return_value = mock_trust_score_result
        mock_trust_scorer_class.return_value = mock_trust_scorer

        response = client.get(
            f"/api/v1/trust/story/{test_story_id}/score?recalculate=true"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["score"] == 0.75
        assert data["confidence"] == 0.9

        # Verify recalculation was performed
        mock_trust_scorer.calculate_score.assert_called_once()
        mock_story_service.update_trust_score.assert_called_once()


class TestTrustLeaderboard:
    """Test /trust/leaderboard endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def sample_stories_list(self):
        """Sample list of stories for leaderboard."""
        return [
            StoryResponse(
                id=str(uuid.uuid4()),
                title=f"Story {i}",
                description=f"Description {i}",
                category="technology",
                trust_score=50.0 + i * 10,
                velocity=1.0,
                geographic_spread={},
                first_seen_at=datetime.now(timezone.utc),
                last_updated_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            )
            for i in range(3)
        ]

    @patch("app.api.v1.endpoints.trust.StoryService")
    def test_trust_leaderboard_success(
        self, mock_story_service_class, client, sample_stories_list
    ):
        """Test trust leaderboard retrieval."""

        mock_story_service = AsyncMock()
        mock_story_service.get_stories.return_value = sample_stories_list
        mock_story_service_class.return_value = mock_story_service

        # Mock database time query
        mock_story_service.db.get_bind.return_value.execute.return_value.scalar.return_value = datetime.now(
            timezone.utc
        )

        response = client.get("/api/v1/trust/leaderboard")

        assert response.status_code == 200
        data = response.json()

        assert "stories" in data
        assert len(data["stories"]) == 3
        assert data["total"] == 3

        # Verify stories are sorted by trust score (descending)
        scores = [story["trust_score"] for story in data["stories"]]
        assert scores == sorted(scores, reverse=True)

    @patch("app.api.v1.endpoints.trust.StoryService")
    def test_trust_leaderboard_with_filters(
        self, mock_story_service_class, client, sample_stories_list
    ):
        """Test trust leaderboard with category filter."""

        mock_story_service = AsyncMock()
        mock_story_service.get_stories.return_value = sample_stories_list
        mock_story_service_class.return_value = mock_story_service
        mock_story_service.db.get_bind.return_value.execute.return_value.scalar.return_value = datetime.now(
            timezone.utc
        )

        response = client.get("/api/v1/trust/leaderboard?limit=5&category=technology")

        assert response.status_code == 200
        data = response.json()

        assert data["category_filter"] == "technology"

        # Verify service was called with correct parameters
        mock_story_service.get_stories.assert_called_once_with(
            skip=0, limit=5, trust_score_min=0.0, category="technology"
        )


class TestBulkCalculateTrustScores:
    """Test /trust/bulk-calculate endpoint."""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @patch("app.api.v1.endpoints.trust.StoryService")
    @patch("app.api.v1.endpoints.trust.TrustScorer")
    def test_bulk_calculate_success(
        self,
        mock_trust_scorer_class,
        mock_story_service_class,
        client,
        sample_story_response,
        mock_trust_score_result,
    ):
        """Test successful bulk trust score calculation."""

        mock_story_service = AsyncMock()
        mock_story_service.get_story_by_id.return_value = sample_story_response
        mock_story_service.update_trust_score.return_value = True
        mock_story_service_class.return_value = mock_story_service

        mock_trust_scorer = AsyncMock()
        mock_trust_scorer.calculate_score.return_value = mock_trust_score_result
        mock_trust_scorer_class.return_value = mock_trust_scorer

        story_ids = [str(uuid.uuid4()) for _ in range(3)]

        response = client.post("/api/v1/trust/bulk-calculate", json=story_ids)

        assert response.status_code == 200
        data = response.json()

        assert data["processed"] == 3
        assert data["errors"] == 0
        assert len(data["results"]) == 3

        # Verify each result has expected structure
        for result in data["results"]:
            assert "story_id" in result
            assert "trust_score" in result
            assert "confidence" in result

    def test_bulk_calculate_too_many_stories(self, client):
        """Test bulk calculation with too many stories."""

        story_ids = [str(uuid.uuid4()) for _ in range(51)]  # More than max of 50

        response = client.post("/api/v1/trust/bulk-calculate", json=story_ids)

        assert response.status_code == 400
        assert "Too many stories" in response.json()["detail"]

    @patch("app.api.v1.endpoints.trust.StoryService")
    @patch("app.api.v1.endpoints.trust.TrustScorer")
    def test_bulk_calculate_with_errors(
        self, mock_trust_scorer_class, mock_story_service_class, client
    ):
        """Test bulk calculation with some errors."""

        story_id_1 = str(uuid.uuid4())
        story_id_2 = str(uuid.uuid4())
        
        mock_story_service = AsyncMock()
        # First story exists, second doesn't
        mock_story_service.get_story_by_id.side_effect = [
            StoryResponse(
                id=story_id_1,
                title="Story 1",
                description="Desc",
                category="tech",
                trust_score=50.0,
                velocity=1.0,
                geographic_spread={},
                first_seen_at=datetime.now(timezone.utc),
                last_updated_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
            ),
            None,  # Story not found
        ]
        mock_story_service.update_trust_score.return_value = True
        mock_story_service_class.return_value = mock_story_service

        mock_trust_scorer = AsyncMock()
        mock_trust_scorer.calculate_score.return_value = {
            "score": 0.8,
            "score_percentage": 80.0,
            "confidence": 0.9,
            "signals": {},
            "explanation": [],
            "calculated_at": "2024-01-01T12:00:00Z",
        }
        mock_trust_scorer_class.return_value = mock_trust_scorer

        story_ids = [story_id_1, story_id_2]

        response = client.post("/api/v1/trust/bulk-calculate", json=story_ids)

        assert response.status_code == 200
        data = response.json()

        assert data["processed"] == 1
        assert data["errors"] == 1
        assert len(data["results"]) == 1
        assert len(data["error_details"]) == 1
        assert f"{story_id_2} not found" in data["error_details"][0]
