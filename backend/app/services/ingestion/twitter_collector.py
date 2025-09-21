"""
Twitter data collection service.
"""

import asyncio
import aiohttp
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, AsyncGenerator
import tweepy
from app.core.config import settings
from app.core.logging import get_logger
from app.models.mongo_models import SocialMediaPost
from app.core.database import get_mongodb_db

logger = get_logger(__name__)


class TwitterCollector:
    """Collects data from Twitter using the API v2."""
    
    def __init__(self):
        self.bearer_token = settings.TWITTER_BEARER_TOKEN
        self.client = None
        self.db = None
        self.rate_limit_remaining = 300  # Default rate limit
        self.rate_limit_reset = datetime.now(timezone.utc)
    
    async def initialize(self):
        """Initialize Twitter client and database connection."""
        if not self.bearer_token:
            raise ValueError("Twitter Bearer Token not configured")
        
        self.client = tweepy.Client(bearer_token=self.bearer_token, wait_on_rate_limit=True)
        self.db = get_mongodb_db()
        logger.info("Twitter collector initialized")
    
    async def collect_trending_tweets(self, country_code: str = "US", limit: int = 100) -> List[Dict[str, Any]]:
        """Collect tweets from trending topics."""
        if not self.client:
            await self.initialize()
        
        try:
            # Get trending topics
            trends = self.client.get_place_trends(id=1)  # 1 = Worldwide, 23424977 = US
            trending_topics = [trend.name for trend in trends[0]["trends"][:10]]
            
            collected_tweets = []
            
            for topic in trending_topics:
                # Search for recent tweets about this topic
                tweets = tweepy.Paginator(
                    self.client.search_recent_tweets,
                    query=f"{topic} -is:retweet lang:en",
                    tweet_fields=["created_at", "author_id", "public_metrics", "context_annotations", "entities"],
                    user_fields=["username", "name", "verified", "public_metrics"],
                    expansions=["author_id"],
                    max_results=min(limit, 100)
                ).flatten(limit=limit)
                
                for tweet in tweets:
                    tweet_data = await self._process_tweet(tweet, topic)
                    if tweet_data:
                        collected_tweets.append(tweet_data)
                
                # Respect rate limits
                await asyncio.sleep(1)
            
            logger.info(f"Collected {len(collected_tweets)} tweets from trending topics")
            return collected_tweets
            
        except Exception as e:
            logger.error(f"Error collecting trending tweets: {e}")
            return []
    
    async def collect_keyword_tweets(self, keywords: List[str], limit: int = 100) -> List[Dict[str, Any]]:
        """Collect tweets for specific keywords."""
        if not self.client:
            await self.initialize()
        
        collected_tweets = []
        
        for keyword in keywords:
            try:
                query = f"{keyword} -is:retweet lang:en"
                tweets = tweepy.Paginator(
                    self.client.search_recent_tweets,
                    query=query,
                    tweet_fields=["created_at", "author_id", "public_metrics", "context_annotations", "entities"],
                    user_fields=["username", "name", "verified", "public_metrics"],
                    expansions=["author_id"],
                    max_results=min(limit, 100)
                ).flatten(limit=limit)
                
                for tweet in tweets:
                    tweet_data = await self._process_tweet(tweet, keyword)
                    if tweet_data:
                        collected_tweets.append(tweet_data)
                
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                logger.error(f"Error collecting tweets for keyword '{keyword}': {e}")
                continue
        
        logger.info(f"Collected {len(collected_tweets)} tweets for keywords")
        return collected_tweets
    
    async def _process_tweet(self, tweet, topic: str) -> Optional[Dict[str, Any]]:
        """Process and normalize tweet data."""
        try:
            # Get user info from includes
            users = {user.id: user for user in tweet.includes.get('users', [])}
            author = users.get(tweet.author_id)
            
            if not author:
                return None
            
            # Extract hashtags and mentions
            hashtags = []
            mentions = []
            if hasattr(tweet, 'entities') and tweet.entities:
                if 'hashtags' in tweet.entities:
                    hashtags = [tag['tag'] for tag in tweet.entities['hashtags']]
                if 'mentions' in tweet.entities:
                    mentions = [mention['username'] for mention in tweet.entities['mentions']]
            
            # Create post document
            post_data = {
                "_id": f"twitter_{tweet.id}",
                "platform": "twitter",
                "external_id": str(tweet.id),
                "author_username": author.username,
                "author_display_name": author.name,
                "content": tweet.text,
                "url": f"https://twitter.com/{author.username}/status/{tweet.id}",
                "posted_at": tweet.created_at,
                "engagement": {
                    "likes": tweet.public_metrics.get("like_count", 0),
                    "retweets": tweet.public_metrics.get("retweet_count", 0),
                    "replies": tweet.public_metrics.get("reply_count", 0),
                    "quotes": tweet.public_metrics.get("quote_count", 0)
                },
                "metadata": {
                    "author_verified": author.verified or False,
                    "author_followers": author.public_metrics.get("followers_count", 0),
                    "topic": topic,
                    "context_annotations": getattr(tweet, 'context_annotations', [])
                },
                "hashtags": hashtags,
                "mentions": mentions,
                "media_urls": [],
                "language": "en",
                "processed": False
            }
            
            return post_data
            
        except Exception as e:
            logger.error(f"Error processing tweet {tweet.id}: {e}")
            return None
    
    async def store_tweets(self, tweets: List[Dict[str, Any]]) -> int:
        """Store tweets in MongoDB."""
        if not tweets:
            return 0
        
        if not self.db:
            self.db = get_mongodb_db()
        
        collection = self.db.social_media_posts
        stored_count = 0
        
        for tweet_data in tweets:
            try:
                # Use upsert to avoid duplicates
                await collection.replace_one(
                    {"_id": tweet_data["_id"]},
                    tweet_data,
                    upsert=True
                )
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Error storing tweet {tweet_data['_id']}: {e}")
        
        logger.info(f"Stored {stored_count} tweets in database")
        return stored_count
    
    async def stream_tweets(self, keywords: List[str]) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream tweets in real-time (placeholder for streaming implementation)."""
        # Note: This would require tweepy.StreamingClient for real streaming
        # For now, implement as periodic collection
        while True:
            tweets = await self.collect_keyword_tweets(keywords, limit=50)
            for tweet in tweets:
                yield tweet
            await asyncio.sleep(60)  # Poll every minute
    
    async def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        if not self.client:
            await self.initialize()
        
        try:
            rate_limits = self.client.get_rate_limit_status()
            return {
                "search_tweets": rate_limits.get("/2/tweets/search/recent", {}),
                "trends": rate_limits.get("/1.1/trends/place", {}),
            }
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {}