"""
News data collector module for RSS feeds and news APIs.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.core.database import get_mongodb_db
from app.core.logging import get_logger

logger = get_logger(__name__)


class NewsCollector:
    """Collects news articles from RSS feeds and news APIs."""

    def __init__(self):
        self.news_api_key = (
            settings.NEWS_API_KEY if hasattr(settings, "NEWS_API_KEY") else None
        )
        self.db = None
        self.http_client = None

        # Major news RSS feeds - no API key required
        self.rss_feeds = {
            # US News
            "CNN Top Stories": "http://rss.cnn.com/rss/cnn_topstories.rss",
            "CNN World": "http://rss.cnn.com/rss/cnn_world.rss",
            "BBC News": "https://feeds.bbci.co.uk/news/rss.xml",
            "BBC World": "https://feeds.bbci.co.uk/news/world/rss.xml",
            "Reuters Top News": "https://feeds.reuters.com/reuters/topNews",
            "Reuters World": "https://feeds.reuters.com/reuters/worldNews",
            "AP News": "https://feeds.apnews.com/rss/apf-topnews",
            "NPR News": "https://feeds.npr.org/1001/rss.xml",
            "The Guardian": "https://www.theguardian.com/world/rss",
            "Al Jazeera": "https://www.aljazeera.com/xml/rss/all.xml",
            # Tech News
            "TechCrunch": "https://techcrunch.com/feed/",
            "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
            "The Verge": "https://www.theverge.com/rss/index.xml",
            "Wired": "https://www.wired.com/feed/rss",
            "Hacker News": "https://hnrss.org/frontpage",
            # Business & Finance
            "Bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
            "Financial Times": "https://www.ft.com/?format=rss",
            "WSJ Markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
            "CNBC Top News": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
            # Science
            "Science Daily": "https://www.sciencedaily.com/rss/all.xml",
            "Nature News": "https://www.nature.com/nature.rss",
            "NASA": "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        }

    async def initialize(self):
        """Initialize HTTP client and database connection."""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.db = get_mongodb_db()
        logger.info("News collector initialized")

    async def collect_rss_feeds(
        self, feed_urls: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        """Collect articles from RSS feeds."""
        if not self.http_client:
            await self.initialize()

        if not feed_urls:
            feed_urls = self.rss_feeds

        collected_articles = []

        for source_name, feed_url in feed_urls.items():
            try:
                logger.info(f"Collecting from {source_name}...")

                # Fetch RSS feed
                response = await self.http_client.get(feed_url)
                response.raise_for_status()

                # Parse feed
                feed = feedparser.parse(response.text)

                # Process entries
                for entry in feed.entries[:20]:  # Limit to 20 articles per source
                    article = await self._process_rss_entry(
                        entry, source_name, feed_url
                    )
                    if article:
                        collected_articles.append(article)

                logger.info(
                    f"Collected {len([a for a in collected_articles if a['source'] == source_name])} articles from {source_name}"
                )

                # Rate limiting
                await asyncio.sleep(1)

            except Exception as e:
                logger.exception(f"Error collecting from {source_name}: {e}")
                continue

        logger.info(
            f"Total collected: {len(collected_articles)} articles from RSS feeds"
        )
        return collected_articles

    async def _process_rss_entry(
        self, entry: Any, source_name: str, feed_url: str
    ) -> dict[str, Any] | None:
        """Process a single RSS feed entry."""
        try:
            # Generate unique ID from URL
            url = entry.get("link", "")
            if not url:
                return None

            article_id = f"news_{hashlib.md5(url.encode()).hexdigest()}"

            # Parse publication date
            published_date = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                import time

                published_date = datetime.fromtimestamp(
                    time.mktime(entry.published_parsed), tz=timezone.utc
                )
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                import time

                published_date = datetime.fromtimestamp(
                    time.mktime(entry.updated_parsed), tz=timezone.utc
                )
            else:
                published_date = datetime.now(timezone.utc)

            # Extract content
            content = entry.get("summary", "")
            if hasattr(entry, "content") and entry.content:
                content = (
                    entry.content[0].value
                    if isinstance(entry.content, list)
                    else entry.content
                )

            # Clean HTML from content
            if content:
                soup = BeautifulSoup(content, "html.parser")
                content = soup.get_text(separator=" ", strip=True)

            # Extract categories/tags
            categories = []
            if hasattr(entry, "tags"):
                categories = [tag.term for tag in entry.tags if hasattr(tag, "term")]

            # Extract author
            author = entry.get("author", "Unknown")
            if hasattr(entry, "authors") and entry.authors:
                author = ", ".join(
                    [a.name for a in entry.authors if hasattr(a, "name")]
                )

            # Create article document
            return {
                "_id": article_id,
                "platform": "news",
                "source": source_name,
                "feed_url": feed_url,
                "title": entry.get("title", "Untitled"),
                "url": url,
                "content": content[:5000],  # Limit content length
                "summary": entry.get("summary", "")[:500],
                "author": author,
                "published_at": published_date,
                "collected_at": datetime.now(timezone.utc),
                "categories": categories,
                "metadata": {
                    "guid": entry.get("id", url),
                    "has_media": bool(entry.get("media_content", [])),
                },
                "processed": False,
                "trust_signals": {
                    "source_credibility": self._get_source_credibility(source_name),
                    "is_major_outlet": source_name
                    in ["CNN Top Stories", "BBC News", "Reuters Top News", "AP News"],
                },
            }

        except Exception as e:
            logger.exception(f"Error processing RSS entry: {e}")
            return None

    def _get_source_credibility(self, source_name: str) -> float:
        """Get credibility score for a news source."""
        # Simple credibility scoring based on source reputation
        high_credibility = [
            "BBC",
            "Reuters",
            "AP News",
            "NPR",
            "The Guardian",
            "Nature",
            "Science Daily",
            "NASA",
        ]
        medium_credibility = [
            "CNN",
            "Al Jazeera",
            "TechCrunch",
            "Ars Technica",
            "The Verge",
            "Wired",
            "Bloomberg",
            "CNBC",
        ]

        for source in high_credibility:
            if source in source_name:
                return 0.9

        for source in medium_credibility:
            if source in source_name:
                return 0.7

        return 0.5  # Default credibility

    async def search_news_by_keywords(
        self, keywords: list[str]
    ) -> list[dict[str, Any]]:
        """Search for news articles by keywords (requires NewsAPI key)."""
        if not self.news_api_key or self.news_api_key == "your-news-api-key":
            logger.warning("NewsAPI key not configured, skipping keyword search")
            return []

        if not self.http_client:
            await self.initialize()

        collected_articles = []

        try:
            # NewsAPI endpoint
            url = "https://newsapi.org/v2/everything"
            params = {
                "q": " OR ".join(keywords),
                "sortBy": "relevancy",
                "language": "en",
                "pageSize": 50,
                "apiKey": self.news_api_key,
            }

            response = await self.http_client.get(url, params=params)
            response.raise_for_status()

            data = response.json()

            if data.get("status") == "ok":
                for article_data in data.get("articles", []):
                    article = await self._process_newsapi_article(
                        article_data, keywords
                    )
                    if article:
                        collected_articles.append(article)

            logger.info(
                f"Collected {len(collected_articles)} articles for keywords: {keywords}"
            )

        except Exception as e:
            logger.exception(f"Error searching news by keywords: {e}")

        return collected_articles

    async def _process_newsapi_article(
        self, article_data: dict, keywords: list[str]
    ) -> dict[str, Any] | None:
        """Process article from NewsAPI response."""
        try:
            url = article_data.get("url", "")
            if not url:
                return None

            article_id = f"news_{hashlib.md5(url.encode()).hexdigest()}"

            # Parse date
            published_at = article_data.get("publishedAt")
            if published_at:
                published_at = datetime.fromisoformat(
                    published_at.replace("Z", "+00:00")
                )
            else:
                published_at = datetime.now(timezone.utc)

            return {
                "_id": article_id,
                "platform": "news",
                "source": article_data.get("source", {}).get("name", "Unknown"),
                "title": article_data.get("title", "Untitled"),
                "url": url,
                "content": article_data.get("content", "")[:5000],
                "summary": article_data.get("description", "")[:500],
                "author": article_data.get("author", "Unknown"),
                "published_at": published_at,
                "collected_at": datetime.now(timezone.utc),
                "image_url": article_data.get("urlToImage"),
                "keywords": keywords,
                "processed": False,
            }

        except Exception as e:
            logger.exception(f"Error processing NewsAPI article: {e}")
            return None

    async def store_articles(self, articles: list[dict[str, Any]]) -> int:
        """Store news articles in MongoDB."""
        if not articles:
            return 0

        if self.db is None:
            self.db = get_mongodb_db()

        collection = self.db.news_articles
        stored_count = 0

        for article in articles:
            try:
                # Use upsert to avoid duplicates
                await collection.replace_one(
                    {"_id": article["_id"]}, article, upsert=True
                )
                stored_count += 1

            except Exception as e:
                logger.exception(f"Error storing article {article['_id']}: {e}")

        logger.info(f"Stored {stored_count} news articles in database")
        return stored_count

    async def get_trending_topics(self) -> list[str]:
        """Extract trending topics from recent news articles."""
        if self.db is None:
            self.db = get_mongodb_db()

        try:
            # Get recent articles
            collection = self.db.news_articles
            recent_articles = (
                await collection.find({}, {"title": 1, "categories": 1})
                .sort("published_at", -1)
                .limit(100)
                .to_list(100)
            )

            # Extract topics from titles and categories
            topics = []
            for article in recent_articles:
                # Add categories
                topics.extend(article.get("categories", []))

                # Extract key words from title (simple approach)
                article.get("title", "")
                # You could use NLP here for better topic extraction

            # Count frequency and return top topics
            from collections import Counter

            topic_counts = Counter(topics)
            return [topic for topic, _ in topic_counts.most_common(10)]

        except Exception as e:
            logger.exception(f"Error getting trending topics: {e}")
            return []

    async def cleanup(self):
        """Cleanup resources."""
        if self.http_client:
            await self.http_client.aclose()
