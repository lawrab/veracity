"""
Main ingestion manager coordinating all data collection.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from typing import Any

from app.core.database import get_mongodb_db, get_redis_client
from app.core.logging import get_logger
from app.services.ingestion.reddit_collector import RedditCollector
from app.services.ingestion.twitter_collector import TwitterCollector
from app.services.processing.nlp_processor import NLPProcessor
from app.services.processing.trend_detector import TrendDetector

logger = get_logger(__name__)


class IngestionManager:
    """Manages the entire data ingestion pipeline."""

    def __init__(self):
        self.twitter_collector = TwitterCollector()
        self.reddit_collector = RedditCollector()
        self.nlp_processor = NLPProcessor()
        self.trend_detector = TrendDetector()
        self.redis = None
        self.mongodb = None
        self.running = False

    async def initialize(self):
        """Initialize all components."""
        try:
            await self.twitter_collector.initialize()
            await self.reddit_collector.initialize()
            await self.nlp_processor.initialize()
            await self.trend_detector.initialize()

            self.redis = get_redis_client()
            self.mongodb = get_mongodb_db()

            logger.info("Ingestion manager initialized successfully")
        except Exception as e:
            logger.exception(f"Failed to initialize ingestion manager: {e}")
            raise

    async def start_collection(self, keywords: list[str] | None = None):
        """Start the main collection loop."""
        if not keywords:
            keywords = [
                "breaking news",
                "urgent",
                "developing",
                "crisis",
                "scandal",
                "controversy",
                "viral",
                "trending",
            ]

        self.running = True
        logger.info("Starting data collection...")

        # Start collection tasks
        tasks = [
            asyncio.create_task(self._collect_social_media(keywords)),
            asyncio.create_task(self._process_collected_data()),
            asyncio.create_task(self._detect_trends()),
            asyncio.create_task(self._cleanup_old_data()),
        ]

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.exception(f"Error in collection loop: {e}")
            self.running = False

    async def stop_collection(self):
        """Stop the collection process."""
        self.running = False
        logger.info("Stopping data collection...")

    async def _collect_social_media(self, keywords: list[str]):
        """Collect data from social media platforms."""
        while self.running:
            try:
                # Collect from Twitter
                twitter_tasks = [
                    self.twitter_collector.collect_trending_tweets(limit=200),
                    self.twitter_collector.collect_keyword_tweets(keywords, limit=300),
                ]
                twitter_results = await asyncio.gather(
                    *twitter_tasks, return_exceptions=True
                )

                all_tweets = []
                for result in twitter_results:
                    if isinstance(result, list):
                        all_tweets.extend(result)

                if all_tweets:
                    await self.twitter_collector.store_tweets(all_tweets)
                    await self._queue_for_processing(all_tweets, "twitter")

                # Collect from Reddit
                reddit_tasks = [
                    self.reddit_collector.collect_trending_posts(limit=200),
                    self.reddit_collector.collect_keyword_posts(keywords, limit=300),
                ]
                reddit_results = await asyncio.gather(
                    *reddit_tasks, return_exceptions=True
                )

                all_posts = []
                for result in reddit_results:
                    if isinstance(result, list):
                        all_posts.extend(result)

                if all_posts:
                    await self.reddit_collector.store_posts(all_posts)
                    await self._queue_for_processing(all_posts, "reddit")

                # Log collection stats
                total_collected = len(all_tweets) + len(all_posts)
                logger.info(
                    f"Collection cycle completed: {total_collected} items collected"
                )

                # Wait before next collection cycle
                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                logger.exception(f"Error in social media collection: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _queue_for_processing(self, items: list[dict[str, Any]], platform: str):
        """Queue items for NLP processing."""
        if not self.redis:
            return

        for item in items:
            try:
                # Add to processing queue
                queue_item = {
                    "item_id": item["_id"],
                    "platform": platform,
                    "content": item["content"],
                    "author": item["author_username"],
                    "posted_at": item["posted_at"].isoformat(),
                    "queued_at": datetime.utcnow().isoformat(),
                }

                await self.redis.lpush("nlp_processing_queue", str(queue_item))

            except Exception as e:
                logger.exception(f"Error queuing item for processing: {e}")

    async def _process_collected_data(self):
        """Process collected data through NLP pipeline."""
        while self.running:
            try:
                if not self.redis:
                    await asyncio.sleep(10)
                    continue

                # Get items from processing queue
                queue_item = await self.redis.brpop("nlp_processing_queue", timeout=10)

                if queue_item:
                    item_data = eval(queue_item[1])  # Convert string back to dict

                    # Process with NLP
                    processed_data = await self.nlp_processor.process_text(
                        item_data["content"],
                        metadata={
                            "item_id": item_data["item_id"],
                            "platform": item_data["platform"],
                            "author": item_data["author"],
                        },
                    )

                    # Update document in MongoDB
                    if processed_data:
                        await self._update_processed_data(
                            item_data["item_id"], processed_data
                        )

            except Exception as e:
                logger.exception(f"Error in data processing: {e}")
                await asyncio.sleep(5)

    async def _update_processed_data(
        self, item_id: str, processed_data: dict[str, Any]
    ):
        """Update processed data in MongoDB."""
        try:
            collection = self.mongodb.social_media_posts
            await collection.update_one(
                {"_id": item_id},
                {
                    "$set": {
                        "sentiment_score": processed_data.get("sentiment"),
                        "entities": processed_data.get("entities", []),
                        "keywords": processed_data.get("keywords", []),
                        "language": processed_data.get("language", "en"),
                        "processed": True,
                        "processed_at": datetime.utcnow(),
                    }
                },
            )
        except Exception as e:
            logger.exception(f"Error updating processed data for {item_id}: {e}")

    async def _detect_trends(self):
        """Detect trends from processed data."""
        while self.running:
            try:
                # Run trend detection every 15 minutes
                await asyncio.sleep(900)

                # Get recent processed posts
                cutoff_time = datetime.utcnow() - timedelta(hours=2)
                collection = self.mongodb.social_media_posts

                recent_posts = await collection.find(
                    {"processed": True, "posted_at": {"$gte": cutoff_time}}
                ).to_list(length=None)

                if recent_posts:
                    trends = await self.trend_detector.detect_trends(recent_posts)

                    for trend in trends:
                        await self._store_trend(trend)

                    logger.info(f"Detected {len(trends)} trends")

            except Exception as e:
                logger.exception(f"Error in trend detection: {e}")

    async def _store_trend(self, trend_data: dict[str, Any]):
        """Store detected trend in database."""
        try:
            # This would integrate with your trend service
            # For now, just log the trend
            logger.info(f"New trend detected: {trend_data.get('keywords', [])}")

        except Exception as e:
            logger.exception(f"Error storing trend: {e}")

    async def _cleanup_old_data(self):
        """Clean up old data to manage storage."""
        while self.running:
            try:
                # Run cleanup daily
                await asyncio.sleep(86400)  # 24 hours

                # Remove posts older than 90 days
                cutoff_date = datetime.utcnow() - timedelta(days=90)
                collection = self.mongodb.social_media_posts

                result = await collection.delete_many(
                    {"posted_at": {"$lt": cutoff_date}}
                )

                logger.info(f"Cleaned up {result.deleted_count} old posts")

            except Exception as e:
                logger.exception(f"Error in data cleanup: {e}")

    async def get_collection_stats(self) -> dict[str, Any]:
        """Get statistics about data collection."""
        try:
            collection = self.mongodb.social_media_posts

            # Count by platform
            platform_stats = await collection.aggregate(
                [
                    {
                        "$group": {
                            "_id": "$platform",
                            "count": {"$sum": 1},
                            "processed": {"$sum": {"$cond": ["$processed", 1, 0]}},
                        }
                    }
                ]
            ).to_list(length=None)

            # Recent activity
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_count = await collection.count_documents(
                {"created_at": {"$gte": one_hour_ago}}
            )

            return {
                "platform_stats": platform_stats,
                "recent_count_1h": recent_count,
                "running": self.running,
                "last_update": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.exception(f"Error getting collection stats: {e}")
            return {}
