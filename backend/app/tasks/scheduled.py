"""
Scheduled tasks for periodic execution via Celery Beat.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.core.database import get_mongodb_db
from app.models.sql_models import Story, TrustSignal
from app.tasks.pipeline import (
    ingest_reddit_data,
    process_posts_to_stories,
    score_stories_trust,
)

logger = get_task_logger(__name__)

# Create async engine for Celery tasks
engine = create_async_engine(settings.POSTGRES_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name="scheduled.reddit_ingestion")
def scheduled_reddit_ingestion():
    """
    Scheduled task to ingest Reddit data periodically.
    Runs every 15 minutes by default.
    """
    logger.info("Running scheduled Reddit ingestion")

    # Define subreddits to monitor
    monitored_subreddits = [
        "worldnews",
        "technology",
        "science",
        "politics",
        "health",
        "economics",
        "environment",
        "AskReddit",
    ]

    # Trigger ingestion task
    result = ingest_reddit_data.delay(
        subreddits=monitored_subreddits,
        limit=50,  # Limit per subreddit to avoid overwhelming
    )

    logger.info(f"Scheduled ingestion started with task ID: {result.id}")
    return {"task_id": str(result.id)}


@celery_app.task(name="scheduled.post_processing")
def scheduled_post_processing():
    """
    Scheduled task to process posts into stories.
    Runs every 10 minutes by default.
    """
    logger.info("Running scheduled post processing")

    # Process up to 100 posts at a time
    result = process_posts_to_stories.delay(limit=100)

    logger.info(f"Scheduled processing started with task ID: {result.id}")
    return {"task_id": str(result.id)}


@celery_app.task(name="scheduled.trust_scoring")
def scheduled_trust_scoring():
    """
    Scheduled task to update trust scores.
    Runs every 5 minutes by default.
    """
    logger.info("Running scheduled trust scoring update")

    # Score all unscored or outdated stories
    result = score_stories_trust.delay(story_ids=None)

    logger.info(f"Scheduled scoring started with task ID: {result.id}")
    return {"task_id": str(result.id)}


@celery_app.task(name="scheduled.cleanup_old_data")
def cleanup_old_data():
    """
    Clean up old data from databases.
    Runs daily at 3 AM by default.
    """
    logger.info("Running scheduled data cleanup")

    try:
        result = asyncio.run(_async_cleanup_old_data())
        logger.info(f"Cleanup completed: {result}")
        return result
    except Exception:
        logger.exception("Cleanup failed")
        raise


async def _async_cleanup_old_data():
    """Async helper for data cleanup."""
    cleanup_stats = {
        "mongodb_posts_deleted": 0,
        "old_stories_deleted": 0,
        "old_trust_scores_deleted": 0,
    }

    # Clean up MongoDB posts older than 7 days
    try:
        mongo_db = get_mongodb_db()
        collection = mongo_db.social_media_posts

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)
        cutoff_timestamp = cutoff_date.timestamp()

        # Delete old processed posts
        result = await collection.delete_many(
            {"created_utc": {"$lt": cutoff_timestamp}, "processed": True}
        )
        cleanup_stats["mongodb_posts_deleted"] = result.deleted_count

    except Exception:
        logger.exception("MongoDB cleanup failed")

    # Clean up PostgreSQL data
    async with AsyncSessionLocal() as db:
        try:
            # Delete stories older than 30 days with low engagement
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)

            old_stories = await db.execute(
                select(Story).where(
                    Story.created_at < cutoff_date,
                    Story.trust_score < 30.0,  # Low trust
                    Story.velocity < 10.0,  # Low engagement
                )
            )
            stories_to_delete = old_stories.scalars().all()

            for story in stories_to_delete:
                await db.delete(story)

            cleanup_stats["old_stories_deleted"] = len(stories_to_delete)

            # Delete trust score history older than 14 days
            trust_cutoff = datetime.now(timezone.utc) - timedelta(days=14)
            result = await db.execute(
                delete(TrustSignal).where(TrustSignal.calculated_at < trust_cutoff)
            )
            cleanup_stats["old_trust_scores_deleted"] = result.rowcount

            await db.commit()

        except Exception:
            logger.exception("PostgreSQL cleanup failed")
            await db.rollback()

    return cleanup_stats


@celery_app.task(name="scheduled.trend_detection")
def detect_emerging_trends():
    """
    Detect emerging trends from recent data.
    Can be scheduled to run every 30 minutes.
    """
    logger.info("Running trend detection")

    try:
        result = asyncio.run(_async_detect_trends())
        logger.info(f"Trend detection completed: {result}")
        return result
    except Exception:
        logger.exception("Trend detection failed")
        raise


async def _async_detect_trends():
    """Async helper for trend detection."""
    async with AsyncSessionLocal() as db:
        # Get recent stories with high velocity
        recent_time = datetime.now(timezone.utc) - timedelta(hours=1)

        trending_stories = await db.execute(
            select(Story)
            .where(Story.created_at > recent_time, Story.velocity > 50.0)
            .order_by(Story.velocity.desc())
            .limit(20)
        )

        trends = [
            {
                "id": str(story.id),
                "title": story.title,
                "category": story.category,
                "velocity": story.velocity,
                "trust_score": story.trust_score,
            }
            for story in trending_stories.scalars()
        ]

        return {
            "trends_detected": len(trends),
            "top_trends": trends[:5],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@celery_app.task(name="scheduled.rescore_stories")
def rescore_old_stories():
    """
    Re-calculate trust scores for stories that haven't been updated recently.
    Can be scheduled to run every hour.
    """
    logger.info("Running story re-scoring")

    try:
        result = asyncio.run(_async_rescore_stories())
        logger.info(f"Re-scoring completed: {result}")
        return result
    except Exception:
        logger.exception("Re-scoring failed")
        raise


async def _async_rescore_stories():
    """Async helper for story re-scoring."""
    async with AsyncSessionLocal() as db:
        # Find stories not updated in the last 2 hours
        update_cutoff = datetime.now(timezone.utc) - timedelta(hours=2)

        stories_to_rescore = await db.execute(
            select(Story).where(Story.updated_at < update_cutoff).limit(50)
        )

        story_ids = [str(story.id) for story in stories_to_rescore.scalars()]

        if story_ids:
            # Trigger trust scoring for these stories
            score_stories_trust.delay(story_ids)

            return {
                "stories_queued_for_rescoring": len(story_ids),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        return {
            "stories_queued_for_rescoring": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
