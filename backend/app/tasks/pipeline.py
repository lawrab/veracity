"""
Pipeline tasks for automated data processing workflow.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from celery import chain
from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import get_mongodb_db
from app.models.story import Story
from app.schemas.story import StoryCreate
from app.schemas.trust import TrustScoreUpdate
from app.services.ingestion.reddit_collector import RedditCollector
from app.services.story_service import StoryService
from app.services.trust_scoring.trust_engine import TrustScoringEngine
from app.services.websocket_manager import websocket_manager

logger = get_task_logger(__name__)

# Create async engine for Celery tasks
engine = create_async_engine(settings.POSTGRES_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(bind=True, name="pipeline.ingest_reddit")
def ingest_reddit_data(self, subreddits: list[str] | None = None, limit: int = 100) -> dict:
    """
    Ingest data from Reddit subreddits.
    
    Args:
        subreddits: List of subreddit names to collect from
        limit: Maximum number of posts per subreddit
    
    Returns:
        Dictionary with ingestion results
    """
    try:
        logger.info(f"Starting Reddit ingestion for {subreddits or 'default subreddits'}")

        # Run async code in sync context
        result = asyncio.run(_async_ingest_reddit(subreddits, limit))

        logger.info(f"Ingested {result['posts_collected']} posts from Reddit")

        # Trigger next step in pipeline automatically
        if result["posts_collected"] > 0:
            process_posts_to_stories.delay()

        return result

    except Exception as e:
        logger.exception("Reddit ingestion failed")
        self.retry(exc=e, countdown=60)


async def _async_ingest_reddit(subreddits: list[str] | None, limit: int) -> dict:
    """Async helper for Reddit ingestion."""
    default_subreddits = ["worldnews", "technology", "science", "politics", "health"]
    subreddits = subreddits or default_subreddits

    collector = RedditCollector()
    collector.db = get_mongodb_db()
    await collector.initialize()

    all_posts = await collector.collect_trending_posts(
        subreddits=subreddits,
        limit=limit
    )

    if all_posts:
        await collector.store_posts(all_posts)

    return {
        "posts_collected": len(all_posts),
        "subreddits": subreddits,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@celery_app.task(bind=True, name="pipeline.process_posts")
def process_posts_to_stories(self, limit: int = 50) -> dict:
    """
    Process raw posts from MongoDB into structured stories in PostgreSQL.
    
    Args:
        limit: Maximum number of posts to process
    
    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Starting post processing (limit: {limit})")

        result = asyncio.run(_async_process_posts(limit))

        logger.info(f"Created {result['stories_created']} stories")

        # Trigger trust scoring for new stories
        if result["stories_created"] > 0:
            score_stories_trust.delay(result["story_ids"])

        return result

    except Exception as e:
        logger.exception("Post processing failed")
        self.retry(exc=e, countdown=60)


async def _async_process_posts(limit: int) -> dict:
    """Async helper for post processing."""
    mongo_db = get_mongodb_db()
    collection = mongo_db.social_media_posts

    # Mark posts as being processed to avoid duplicates
    posts = await collection.find(
        {"processed": {"$ne": True}}
    ).limit(limit).to_list(length=limit)

    if not posts:
        return {"stories_created": 0, "story_ids": []}

    async with AsyncSessionLocal() as db:
        story_service = StoryService(db)
        stories_created = 0
        story_ids = []

        for post in posts:
            try:
                # Check if story already exists for this content
                existing = await db.execute(
                    select(Story).where(Story.title == post.get("title", "")[:200])
                )
                if existing.scalar_one_or_none():
                    continue

                # Create story from post
                title = post.get("title", post.get("content", "Untitled"))[:200]
                score = post.get("score", 0)
                comments = post.get("num_comments", 1)
                velocity = score / max(1, comments)

                story_data = StoryCreate(
                    title=title,
                    description=post.get("content", "")[:1000],
                    category=post.get("subreddit", "general"),
                    trust_score=50.0,  # Initial neutral score
                    velocity=velocity,
                    first_seen_at=datetime.fromtimestamp(
                        post.get("created_utc", datetime.now(timezone.utc).timestamp()),
                        tz=timezone.utc,
                    ),
                )

                story = await story_service.create_story(story_data)
                stories_created += 1
                story_ids.append(str(story.id))

                # Mark post as processed
                await collection.update_one(
                    {"_id": post["_id"]},
                    {"$set": {"processed": True, "story_id": str(story.id)}}
                )

                # Send WebSocket update
                await websocket_manager.broadcast_story_update({
                    "type": "story_created",
                    "story_id": str(story.id),
                    "title": story.title,
                    "category": story.category,
                })

            except Exception:
                logger.exception(
                    f"Failed to create story from post {post.get('id')}"
                )
                continue

        await db.commit()

    return {
        "stories_created": stories_created,
        "story_ids": story_ids,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@celery_app.task(bind=True, name="pipeline.score_trust")
def score_stories_trust(self, story_ids: list[str] | None = None) -> dict:
    """
    Calculate trust scores for stories.
    
    Args:
        story_ids: List of story IDs to score, or None for all unscored
    
    Returns:
        Dictionary with scoring results
    """
    try:
        logger.info(f"Starting trust scoring for {len(story_ids) if story_ids else 'all'} stories")

        result = asyncio.run(_async_score_trust(story_ids))

        logger.info(f"Scored {result['stories_scored']} stories")

        return result

    except Exception as e:
        logger.exception("Trust scoring failed")
        self.retry(exc=e, countdown=60)


async def _async_score_trust(story_ids: list[str] | None) -> dict:
    """Async helper for trust scoring."""
    async with AsyncSessionLocal() as db:
        # Get stories to score
        query = select(Story)
        if story_ids:
            from uuid import UUID
            query = query.where(Story.id.in_([UUID(sid) for sid in story_ids]))
        else:
            # Score stories with default trust score
            query = query.where(Story.trust_score == 50.0)

        result = await db.execute(query)
        stories = result.scalars().all()

        if not stories:
            return {"stories_scored": 0}

        # Initialize trust engine
        engine = TrustScoringEngine(db)
        stories_scored = 0

        for story in stories:
            try:
                # Calculate comprehensive trust score
                trust_data = await engine.calculate_trust_score(story.id)

                if trust_data:
                    # Update story with new trust score
                    story.trust_score = trust_data.overall_score
                    story.updated_at = datetime.now(timezone.utc)

                    # Store trust score history
                    await engine.store_trust_score(
                        TrustScoreUpdate(
                            story_id=story.id,
                            overall_score=trust_data.overall_score,
                            source_credibility=trust_data.source_credibility,
                            content_consistency=trust_data.content_consistency,
                            social_verification=trust_data.social_verification,
                            expert_validation=trust_data.expert_validation,
                            factors=trust_data.factors,
                        )
                    )

                    stories_scored += 1

                    # Send WebSocket update
                    await websocket_manager.broadcast_trust_score_update({
                        "story_id": str(story.id),
                        "trust_score": trust_data.overall_score,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

            except Exception:
                logger.exception(f"Failed to score story {story.id}")
                continue

        await db.commit()

    return {
        "stories_scored": stories_scored,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@celery_app.task(name="pipeline.run_full_pipeline")
def run_full_pipeline(subreddits: list[str] | None = None) -> str:
    """
    Run the complete data pipeline: ingest → process → score.
    
    Args:
        subreddits: Optional list of subreddits to monitor
    
    Returns:
        Pipeline execution ID
    """
    logger.info("Starting full pipeline execution")

    # Create pipeline chain
    pipeline = chain(
        ingest_reddit_data.s(subreddits=subreddits, limit=100),
        process_posts_to_stories.s(),
        score_stories_trust.s(),
    )

    # Execute pipeline
    result = pipeline.apply_async()

    return str(result.id)


@celery_app.task(name="pipeline.analyze_url")
def analyze_url(url: str, user_id: str | None = None) -> dict:
    """
    Analyze a specific URL submitted by a user.
    
    Args:
        url: URL to analyze
        user_id: Optional user ID who submitted the URL
    
    Returns:
        Analysis results
    """
    try:
        logger.info(f"Analyzing URL: {url}")

        result = asyncio.run(_async_analyze_url(url, user_id))

        return result

    except Exception:
        logger.exception("URL analysis failed")
        raise


async def _async_analyze_url(url: str, user_id: str | None) -> dict:  # noqa: ARG001
    """Async helper for URL analysis."""
    # This would integrate with news article parsing and fact-checking
    # For now, return a placeholder
    return {
        "url": url,
        "status": "pending_implementation",
        "message": "URL analysis will be implemented with news correlation system",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
