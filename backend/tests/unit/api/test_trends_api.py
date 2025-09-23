"""Unit tests for trends API endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestTrendsAPI:
    """Test cases for trends API endpoints."""

    @pytest.mark.unit
    def test_get_trends_endpoint(self, client: TestClient):
        """Test GET /api/v1/trends endpoint."""
        with patch("app.api.v1.trends.TrendService") as mock_service:
            mock_trends = [
                {
                    "id": 1,
                    "name": "AI Revolution",
                    "keywords": ["AI", "technology"],
                    "score": 0.95,
                    "platform": "twitter",
                    "post_count": 1500,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                {
                    "id": 2,
                    "name": "Climate Change",
                    "keywords": ["climate", "environment"],
                    "score": 0.88,
                    "platform": "reddit",
                    "post_count": 1200,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            ]
            mock_service.return_value.get_trending_topics = AsyncMock(
                return_value=mock_trends
            )

            response = client.get("/api/v1/trends")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["name"] == "AI Revolution"
            assert data[0]["score"] > data[1]["score"]

    @pytest.mark.unit
    def test_get_trends_with_filters(self, client: TestClient):
        """Test GET /api/v1/trends with query parameters."""
        response = client.get(
            "/api/v1/trends",
            params={"platform": "twitter", "limit": 5, "min_score": 0.8},
        )

        assert response.status_code == 200
        # Verify query params were processed

    @pytest.mark.unit
    def test_get_trend_by_id(self, client: TestClient):
        """Test GET /api/v1/trends/{trend_id} endpoint."""
        with patch("app.api.v1.trends.TrendService") as mock_service:
            mock_trend = {
                "id": 1,
                "name": "AI Revolution",
                "keywords": ["AI", "technology"],
                "score": 0.95,
                "platform": "twitter",
                "post_count": 1500,
                "growth_rate": 1.5,
                "related_stories": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            mock_service.return_value.get_trend_by_id = AsyncMock(
                return_value=mock_trend
            )

            response = client.get("/api/v1/trends/1")

            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["name"] == "AI Revolution"

    @pytest.mark.unit
    def test_get_trend_not_found(self, client: TestClient):
        """Test GET /api/v1/trends/{trend_id} with non-existent ID."""
        with patch("app.api.v1.trends.TrendService") as mock_service:
            mock_service.return_value.get_trend_by_id = AsyncMock(return_value=None)

            response = client.get("/api/v1/trends/999")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.unit
    def test_create_trend_detection_job(self, client: TestClient, auth_headers):
        """Test POST /api/v1/trends/detect endpoint."""
        with patch("app.api.v1.trends.TrendService") as mock_service:
            mock_service.return_value.detect_trends = AsyncMock(
                return_value={"job_id": "job123", "status": "processing"}
            )

            response = client.post(
                "/api/v1/trends/detect",
                json={
                    "platforms": ["twitter", "reddit"],
                    "keywords": ["AI", "technology"],
                    "time_range": "1h",
                },
                headers=auth_headers,
            )

            assert response.status_code == 202
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "processing"

    @pytest.mark.unit
    def test_get_trend_history(self, client: TestClient):
        """Test GET /api/v1/trends/{trend_id}/history endpoint."""
        with patch("app.api.v1.trends.TrendService") as mock_service:
            mock_history = [
                {"timestamp": "2025-01-22T10:00:00Z", "score": 0.8, "post_count": 100},
                {"timestamp": "2025-01-22T11:00:00Z", "score": 0.85, "post_count": 150},
                {"timestamp": "2025-01-22T12:00:00Z", "score": 0.95, "post_count": 200},
            ]
            mock_service.return_value.get_trend_history = AsyncMock(
                return_value=mock_history
            )

            response = client.get("/api/v1/trends/1/history")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 3
            assert data[2]["score"] > data[0]["score"]

    @pytest.mark.unit
    def test_get_emerging_trends(self, client: TestClient):
        """Test GET /api/v1/trends/emerging endpoint."""
        with patch("app.api.v1.trends.TrendService") as mock_service:
            mock_emerging = [
                {
                    "name": "New Tech Breakthrough",
                    "keywords": ["breakthrough", "innovation"],
                    "score": 0.7,
                    "growth_rate": 3.5,
                    "platform": "twitter",
                }
            ]
            mock_service.return_value.identify_emerging_trends = AsyncMock(
                return_value=mock_emerging
            )

            response = client.get("/api/v1/trends/emerging")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["growth_rate"] > 2.0

    @pytest.mark.unit
    def test_invalid_platform_filter(self, client: TestClient):
        """Test invalid platform filter returns 422."""
        response = client.get("/api/v1/trends", params={"platform": "invalid_platform"})

        assert response.status_code == 422

    @pytest.mark.unit
    def test_trends_pagination(self, client: TestClient):
        """Test pagination for trends endpoint."""
        response = client.get("/api/v1/trends", params={"offset": 10, "limit": 20})

        assert response.status_code == 200
        # Verify pagination metadata in response
