"""
Reddit data collection service.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

import praw

from app.core.config import settings
from app.core.database import get_mongodb_db
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedditCollector:
    """Collects data from Reddit using PRAW."""

    def __init__(self):
        self.client_id = settings.REDDIT_CLIENT_ID
        self.client_secret = settings.REDDIT_CLIENT_SECRET
        self.reddit = None
        self.db = None

    async def initialize(self):
        """Initialize Reddit client and database connection."""
        if not self.client_id or not self.client_secret:
            msg = "Reddit API credentials not configured"
            raise ValueError(msg)

        self.reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent="Veracity:v1.0.0 (by /u/veracity_bot)",
        )

        self.db = get_mongodb_db()
        logger.info("Reddit collector initialized")

    async def collect_trending_posts(
        self, subreddits: list[str] | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """Collect trending posts from specified subreddits."""
        if not self.reddit:
            await self.initialize()

        if not subreddits:
            # Default subreddits for news and trends
            subreddits = [
                "news",
                "worldnews",
                "politics",
                "technology",
                "breakingnews",
                "trending",
                "popular",
            ]

        collected_posts = []

        for subreddit_name in subreddits:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)

                # Get hot posts
                for post in subreddit.hot(limit=limit // len(subreddits)):
                    post_data = await self._process_post(post, subreddit_name)
                    if post_data:
                        collected_posts.append(post_data)

                # Get rising posts (potential trends)
                for post in subreddit.rising(limit=limit // len(subreddits) // 2):
                    post_data = await self._process_post(post, subreddit_name)
                    if post_data:
                        collected_posts.append(post_data)

                await asyncio.sleep(1)  # Rate limiting

            except Exception as e:
                logger.exception(
                    f"Error collecting from subreddit '{subreddit_name}': {e}"
                )
                continue

        logger.info(f"Collected {len(collected_posts)} Reddit posts")
        return collected_posts

    async def collect_keyword_posts(
        self, keywords: list[str], limit: int = 100
    ) -> list[dict[str, Any]]:
        """Collect posts containing specific keywords."""
        if not self.reddit:
            await self.initialize()

        collected_posts = []

        for keyword in keywords:
            try:
                # Search across Reddit
                search_results = self.reddit.subreddit("all").search(
                    keyword, sort="new", time_filter="day", limit=limit // len(keywords)
                )

                for post in search_results:
                    post_data = await self._process_post(post, keyword)
                    if post_data:
                        collected_posts.append(post_data)

                await asyncio.sleep(1)  # Rate limiting

            except Exception as e:
                logger.exception(f"Error searching for keyword '{keyword}': {e}")
                continue

        logger.info(f"Collected {len(collected_posts)} Reddit posts for keywords")
        return collected_posts

    async def _process_post(self, post, context: str) -> dict[str, Any] | None:
        """Process and normalize Reddit post data."""
        try:
            # Skip removed/deleted posts
            if post.selftext in {"[deleted]", "[removed]"}:
                return None

            # Combine title and content
            content = post.title
            if post.selftext and post.selftext.strip():
                content += f"\n\n{post.selftext}"

            # Extract post URL
            post_url = f"https://reddit.com{post.permalink}"

            # Create post document
            return {
                "_id": f"reddit_{post.id}",
                "platform": "reddit",
                "external_id": post.id,
                "author_username": str(post.author) if post.author else "[deleted]",
                "author_display_name": str(post.author) if post.author else "[deleted]",
                "content": content,
                "url": post_url,
                "posted_at": datetime.fromtimestamp(post.created_utc, tz=timezone.utc),
                "engagement": {
                    "upvotes": post.ups,
                    "downvotes": post.downs,
                    "comments": post.num_comments,
                    "score": post.score,
                    "upvote_ratio": post.upvote_ratio,
                },
                "metadata": {
                    "subreddit": post.subreddit.display_name,
                    "subreddit_subscribers": post.subreddit.subscribers,
                    "is_self": post.is_self,
                    "is_video": post.is_video,
                    "over_18": post.over_18,
                    "spoiler": post.spoiler,
                    "stickied": post.stickied,
                    "context": context,
                    "flair": post.link_flair_text,
                    "gilded": post.gilded,
                    "awards": post.total_awards_received,
                },
                "hashtags": self._extract_hashtags(content),
                "mentions": self._extract_mentions(content),
                "media_urls": self._extract_media_urls(post),
                "language": "en",  # Reddit is primarily English
                "processed": False,
            }

        except Exception as e:
            logger.exception(f"Error processing Reddit post {post.id}: {e}")
            return None

    def _extract_hashtags(self, content: str) -> list[str]:
        """Extract hashtag-like patterns from content."""
        import re

        # Reddit doesn't have hashtags, but we can look for r/ subreddit mentions
        subreddit_pattern = r"r/([A-Za-z0-9_]+)"
        return re.findall(subreddit_pattern, content)

    def _extract_mentions(self, content: str) -> list[str]:
        """Extract user mentions from content."""
        import re

        mention_pattern = r"u/([A-Za-z0-9_-]+)"
        return re.findall(mention_pattern, content)

    def _extract_media_urls(self, post) -> list[str]:
        """Extract media URLs from post."""
        urls = []

        # Post URL if it's a link post
        if not post.is_self and post.url:
            urls.append(post.url)

        # Check for preview images
        if hasattr(post, "preview") and post.preview:
            try:
                images = post.preview.get("images", [])
                for image in images:
                    if "source" in image:
                        urls.append(image["source"]["url"])
            except:
                pass

        return urls

    async def store_posts(self, posts: list[dict[str, Any]]) -> int:
        """Store Reddit posts in MongoDB."""
        if not posts:
            return 0

        if self.db is None:
            self.db = get_mongodb_db()

        collection = self.db.social_media_posts
        stored_count = 0

        for post_data in posts:
            try:
                # Use upsert to avoid duplicates
                await collection.replace_one(
                    {"_id": post_data["_id"]}, post_data, upsert=True
                )
                stored_count += 1

            except Exception as e:
                logger.exception(f"Error storing Reddit post {post_data['_id']}: {e}")

        logger.info(f"Stored {stored_count} Reddit posts in database")
        return stored_count

    async def monitor_subreddits(
        self, subreddits: list[str]
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Monitor subreddits for new posts."""
        if not self.reddit:
            await self.initialize()

        seen_posts = set()

        while True:
            for subreddit_name in subreddits:
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)

                    # Check new posts
                    for post in subreddit.new(limit=10):
                        if post.id not in seen_posts:
                            seen_posts.add(post.id)
                            post_data = await self._process_post(post, subreddit_name)
                            if post_data:
                                yield post_data

                except Exception as e:
                    logger.exception(
                        f"Error monitoring subreddit '{subreddit_name}': {e}"
                    )

                await asyncio.sleep(2)  # Rate limiting

            await asyncio.sleep(30)  # Check every 30 seconds

    async def get_subreddit_info(
        self, subreddit_names: list[str]
    ) -> dict[str, dict[str, Any]]:
        """Get information about subreddits."""
        if not self.reddit:
            await self.initialize()

        subreddit_info = {}

        for subreddit_name in subreddit_names:
            try:
                subreddit = self.reddit.subreddit(subreddit_name)
                subreddit_info[subreddit_name] = {
                    "display_name": subreddit.display_name,
                    "title": subreddit.title,
                    "description": subreddit.public_description,
                    "subscribers": subreddit.subscribers,
                    "active_users": subreddit.active_user_count,
                    "created_utc": subreddit.created_utc,
                    "over_18": subreddit.over18,
                    "lang": subreddit.lang,
                }
            except Exception as e:
                logger.exception(
                    f"Error getting info for subreddit '{subreddit_name}': {e}"
                )
                subreddit_info[subreddit_name] = None

        return subreddit_info
