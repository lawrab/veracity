#!/usr/bin/env python
"""Test script for Reddit data collector."""
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.ingestion.reddit_collector import RedditCollector
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_reddit_collector():
    """Test Reddit collector functionality."""
    collector = RedditCollector()
    
    try:
        logger.info("Initializing Reddit collector...")
        await collector.initialize()
        logger.info("✓ Successfully initialized Reddit collector")
        
        # Test 1: Collect trending posts from popular subreddits
        logger.info("\nCollecting trending posts from popular subreddits...")
        trending_posts = await collector.collect_trending_posts(
            subreddits=["news", "technology"], 
            limit=10
        )
        logger.info(f"✓ Collected {len(trending_posts)} trending posts")
        
        if trending_posts:
            sample_post = trending_posts[0]
            logger.info(f"Sample post:")
            logger.info(f"  - Subreddit: r/{sample_post['metadata']['subreddit']}")
            logger.info(f"  - Title: {sample_post['content'][:100]}...")
            logger.info(f"  - Upvotes: {sample_post['engagement']['upvotes']}")
            logger.info(f"  - Comments: {sample_post['engagement']['comments']}")
        
        # Test 2: Search for specific keywords
        logger.info("\nSearching for posts about 'technology'...")
        keyword_posts = await collector.collect_keyword_posts(
            keywords=["technology", "AI"],
            limit=5
        )
        logger.info(f"✓ Collected {len(keyword_posts)} posts with keywords")
        
        # Test 3: Monitor specific subreddits
        logger.info("\nCollecting from specific subreddits...")
        subreddits = ["technology", "worldnews", "science"]
        monitored_posts = await collector.monitor_subreddits(
            subreddits=subreddits,
            posts_per_sub=3
        )
        logger.info(f"✓ Collected {len(monitored_posts)} posts from {len(subreddits)} subreddits")
        
        # Test 4: Store posts in MongoDB
        if trending_posts:
            logger.info("\nTesting MongoDB storage...")
            stored = await collector.store_posts(trending_posts[:3])
            logger.info(f"✓ Successfully stored {stored} posts to MongoDB")
        
        # Test 5: Get subreddit info
        logger.info("\nGetting subreddit information...")
        subreddit_info = await collector.get_subreddit_info("technology")
        if subreddit_info:
            logger.info(f"✓ r/technology info:")
            logger.info(f"  - Subscribers: {subreddit_info.get('subscribers', 'N/A'):,}")
            logger.info(f"  - Description: {subreddit_info.get('description', '')[:100]}...")
        
        logger.info("\n✅ All tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Check if Reddit credentials are set
    if not os.getenv("REDDIT_CLIENT_ID") or os.getenv("REDDIT_CLIENT_ID") == "your-reddit-client-id":
        logger.error("❌ Reddit credentials not configured in .env file")
        sys.exit(1)
    
    success = asyncio.run(test_reddit_collector())
    sys.exit(0 if success else 1)