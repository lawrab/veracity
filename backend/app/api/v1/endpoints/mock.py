"""
Mock endpoints for testing frontend without database dependencies.
"""

from datetime import datetime, timedelta
from typing import List
import random
from fastapi import APIRouter

router = APIRouter()


@router.get("/stories/trending")
async def get_mock_trending_stories():
    """Return mock trending stories data."""
    
    categories = ["Politics", "Technology", "Health", "Sports", "Entertainment", "Science"]
    
    stories = []
    for i in range(12):
        story = {
            "id": f"story_{i + 1}",
            "title": f"Breaking: Mock Story {i + 1} - {random.choice(['Major Development', 'Important Update', 'Critical Analysis'])}",
            "description": f"This is a mock story description for testing purposes. It contains enough text to show how the story card handles longer descriptions in the frontend interface.",
            "category": random.choice(categories),
            "trust_score": round(random.uniform(20, 95), 1),
            "velocity": round(random.uniform(0.1, 15.0), 1),
            "geographic_spread": {
                "US": round(random.uniform(20, 80), 1),
                "EU": round(random.uniform(10, 60), 1),
                "Asia": round(random.uniform(5, 40), 1)
            } if random.choice([True, False]) else None,
            "first_seen_at": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat(),
            "last_updated_at": (datetime.now() - timedelta(minutes=random.randint(5, 120))).isoformat(),
            "created_at": (datetime.now() - timedelta(hours=random.randint(2, 72))).isoformat()
        }
        stories.append(story)
    
    return {"data": stories}


@router.get("/trends/live")
async def get_mock_live_trends():
    """Return mock trending topics data."""
    
    trend_names = [
        "AI Revolution", "Climate Action", "Space Exploration", "Cryptocurrency",
        "Remote Work", "Electric Vehicles", "Social Media", "Healthcare Reform",
        "Tech Regulation", "Green Energy", "Digital Privacy", "Virtual Reality"
    ]
    
    trends = []
    for i in range(8):
        trend = {
            "id": f"trend_{i + 1}",
            "name": random.choice(trend_names),
            "description": f"Mock trending topic #{i + 1} for testing the dashboard",
            "category": random.choice(["Technology", "Politics", "Environment", "Business"]),
            "confidence_score": round(random.uniform(50, 95), 1),
            "story_count": random.randint(5, 50),
            "platform_distribution": {
                "Twitter": round(random.uniform(20, 60), 1),
                "Reddit": round(random.uniform(10, 40), 1),
                "TikTok": round(random.uniform(5, 30), 1),
                "Instagram": round(random.uniform(5, 25), 1)
            },
            "peak_velocity": round(random.uniform(1.0, 25.0), 1),
            "keywords": random.sample(["trending", "viral", "breaking", "update", "news", "analysis", "report"], 3),
            "detected_at": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
            "last_updated_at": (datetime.now() - timedelta(minutes=random.randint(1, 60))).isoformat(),
            "created_at": (datetime.now() - timedelta(hours=random.randint(2, 48))).isoformat()
        }
        trends.append(trend)
    
    return {"data": trends}


@router.get("/health/check")
async def mock_health_check():
    """Mock health check that always returns healthy."""
    return {
        "status": "healthy",
        "api": True,
        "database": True,
        "redis": True,
        "elasticsearch": True
    }