#!/usr/bin/env python
"""Test script for News RSS feed collector."""
import asyncio
import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.ingestion.news_collector import NewsCollector
from app.core.logging import get_logger

logger = get_logger(__name__)


async def test_news_collector():
    """Test News collector functionality."""
    collector = NewsCollector()
    
    try:
        logger.info("Initializing News collector...")
        await collector.initialize()
        logger.info("✓ Successfully initialized News collector")
        
        # Test with a subset of RSS feeds for quick testing
        test_feeds = {
            "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
            "Reuters Top News": "https://feeds.reuters.com/reuters/topNews",
            "TechCrunch": "https://techcrunch.com/feed/",
        }
        
        # Test 1: Collect from RSS feeds
        logger.info("\nCollecting news from RSS feeds...")
        articles = await collector.collect_rss_feeds(test_feeds)
        logger.info(f"✓ Collected {len(articles)} articles from RSS feeds")
        
        if articles:
            # Show sample articles
            logger.info("\nSample articles collected:")
            for article in articles[:3]:
                logger.info(f"\n  📰 {article['title'][:80]}...")
                logger.info(f"     Source: {article['source']}")
                logger.info(f"     URL: {article['url']}")
                logger.info(f"     Published: {article['published_at']}")
                logger.info(f"     Credibility: {article.get('trust_signals', {}).get('source_credibility', 'N/A')}")
        
        # Test 2: Store articles in MongoDB
        if articles:
            logger.info("\n\nTesting MongoDB storage...")
            stored = await collector.store_articles(articles[:10])  # Store first 10
            logger.info(f"✓ Successfully stored {stored} articles to MongoDB")
        
        # Test 3: Get trending topics
        logger.info("\nExtracting trending topics...")
        trending = await collector.get_trending_topics()
        if trending:
            logger.info(f"✓ Trending topics: {', '.join(trending[:5])}")
        
        # Test 4: Search by keywords (only if API key is configured)
        if collector.news_api_key and collector.news_api_key != "your-news-api-key":
            logger.info("\nSearching for articles with keywords...")
            keyword_articles = await collector.search_news_by_keywords(["technology", "AI"])
            logger.info(f"✓ Found {len(keyword_articles)} articles matching keywords")
        else:
            logger.info("\nℹ️  NewsAPI key not configured, skipping keyword search")
        
        logger.info("\n✅ All tests passed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await collector.cleanup()


if __name__ == "__main__":
    success = asyncio.run(test_news_collector())
    sys.exit(0 if success else 1)