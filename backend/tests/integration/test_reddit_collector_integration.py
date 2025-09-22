"""Integration tests for Reddit collector."""
import pytest
import os
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timezone

from app.services.ingestion.reddit_collector import RedditCollector
from app.core.config import settings


@pytest.mark.integration
class TestRedditCollectorIntegration:
    """Integration tests for Reddit data collection."""
    
    @pytest.fixture
    async def reddit_collector(self, mongodb_client):
        """Create Reddit collector with real MongoDB connection."""
        collector = RedditCollector()
        collector.mongodb = mongodb_client
        yield collector
    
    @pytest.fixture
    def mock_reddit_api(self):
        """Mock Reddit API responses."""
        mock_submission = MagicMock()
        mock_submission.title = "Test Post Title"
        mock_submission.selftext = "Test post content"
        mock_submission.author = MagicMock(name="test_user")
        mock_submission.created_utc = datetime.now(timezone.utc).timestamp()
        mock_submission.score = 1000
        mock_submission.num_comments = 50
        mock_submission.subreddit = MagicMock(display_name="technology")
        mock_submission.id = "test123"
        mock_submission.url = "https://reddit.com/r/technology/test123"
        return mock_submission
    
    @pytest.mark.skipif(
        not os.getenv("REDDIT_CLIENT_ID") or os.getenv("REDDIT_CLIENT_ID") == "your-reddit-client-id",
        reason="Reddit API credentials not configured"
    )
    async def test_initialize_with_real_credentials(self):
        """Test initialization with real Reddit credentials."""
        collector = RedditCollector()
        await collector.initialize()
        assert collector.reddit is not None
        assert collector.initialized is True
    
    async def test_collect_and_store_posts(self, reddit_collector, mock_reddit_api, mongodb_client):
        """Test collecting posts and storing in MongoDB."""
        with patch.object(reddit_collector, 'reddit') as mock_reddit:
            mock_subreddit = MagicMock()
            mock_subreddit.hot.return_value = [mock_reddit_api]
            mock_reddit.subreddit.return_value = mock_subreddit
            
            posts = await reddit_collector.collect_trending_posts(
                subreddits=["technology"],
                limit=1
            )
            
            assert len(posts) == 1
            assert posts[0]["platform"] == "reddit"
            assert posts[0]["content"] == "Test Post Title"
            
            # Store in MongoDB
            stored = await reddit_collector.store_posts(posts)
            assert stored == 1
            
            # Verify stored in database
            stored_post = await mongodb_client.social_posts.find_one(
                {"post_id": "reddit_test123"}
            )
            assert stored_post is not None
            assert stored_post["content"] == "Test Post Title"
    
    async def test_collect_with_keywords(self, reddit_collector, mock_reddit_api):
        """Test collecting posts with keyword filtering."""
        with patch.object(reddit_collector, 'reddit') as mock_reddit:
            mock_reddit.subreddit.return_value.search.return_value = [mock_reddit_api]
            
            posts = await reddit_collector.collect_keyword_posts(
                keywords=["technology"],
                limit=1
            )
            
            assert len(posts) == 1
            assert any("technology" in str(v).lower() 
                      for v in posts[0].values() if v)
    
    async def test_monitor_multiple_subreddits(self, reddit_collector, mock_reddit_api):
        """Test monitoring multiple subreddits concurrently."""
        with patch.object(reddit_collector, 'reddit') as mock_reddit:
            mock_subreddit = MagicMock()
            mock_subreddit.new.return_value = [mock_reddit_api]
            mock_reddit.subreddit.return_value = mock_subreddit
            
            posts = await reddit_collector.monitor_subreddits(
                subreddits=["technology", "science", "worldnews"],
                posts_per_sub=2
            )
            
            # Should get posts from all subreddits
            assert len(posts) > 0
            platforms = [p["metadata"]["subreddit"] for p in posts]
            assert "technology" in platforms
    
    async def test_get_subreddit_info(self, reddit_collector):
        """Test retrieving subreddit information."""
        with patch.object(reddit_collector, 'reddit') as mock_reddit:
            mock_subreddit = MagicMock()
            mock_subreddit.display_name = "technology"
            mock_subreddit.subscribers = 15000000
            mock_subreddit.public_description = "Tech news and discussion"
            mock_reddit.subreddit.return_value = mock_subreddit
            
            info = await reddit_collector.get_subreddit_info("technology")
            
            assert info["name"] == "technology"
            assert info["subscribers"] == 15000000
            assert "Tech news" in info["description"]
    
    async def test_error_handling_invalid_subreddit(self, reddit_collector):
        """Test error handling for invalid subreddit."""
        with patch.object(reddit_collector, 'reddit') as mock_reddit:
            mock_reddit.subreddit.side_effect = Exception("Subreddit not found")
            
            posts = await reddit_collector.collect_trending_posts(
                subreddits=["invalid_subreddit_12345"],
                limit=10
            )
            
            assert posts == []
    
    async def test_rate_limiting(self, reddit_collector):
        """Test rate limiting handling."""
        with patch.object(reddit_collector, '_rate_limit_delay') as mock_delay:
            mock_delay.return_value = None
            
            # Simulate multiple rapid requests
            for _ in range(5):
                await reddit_collector.collect_trending_posts(
                    subreddits=["technology"],
                    limit=1
                )
            
            # Should have applied rate limiting
            assert mock_delay.call_count > 0
    
    async def test_data_transformation(self, reddit_collector, mock_reddit_api):
        """Test data transformation to standard format."""
        transformed = reddit_collector._transform_post(mock_reddit_api)
        
        assert transformed["platform"] == "reddit"
        assert transformed["post_id"].startswith("reddit_")
        assert "content" in transformed
        assert "engagement" in transformed
        assert transformed["engagement"]["upvotes"] == 1000
        assert transformed["engagement"]["comments"] == 50
        assert "metadata" in transformed
        assert transformed["metadata"]["subreddit"] == "technology"