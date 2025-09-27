"""
Ingestion API endpoints.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.core.database import get_mongodb_db
from app.core.logging import get_logger
from app.schemas.ingestion import (
    CollectedDataSummary,
    CollectorStatus,
    IngestionRequest,
    IngestionResponse,
    IngestionStatus,
)
from app.services.ingestion.reddit_collector import RedditCollector

logger = get_logger(__name__)

router = APIRouter()

# Track ingestion status
ingestion_status: dict[str, CollectorStatus] = {
    "reddit": CollectorStatus.IDLE,
    "twitter": CollectorStatus.IDLE,
    "news": CollectorStatus.IDLE,
}


@router.get("/status", response_model=IngestionStatus)
async def get_ingestion_status():
    """Get the current status of all data collectors."""
    return IngestionStatus(collectors=ingestion_status)


@router.post("/reddit", response_model=IngestionResponse)
async def ingest_reddit(request: IngestionRequest, background_tasks: BackgroundTasks):
    """
    Trigger Reddit data collection for specified subreddits.
    """
    # Check if Reddit collector is already running
    if ingestion_status["reddit"] == CollectorStatus.RUNNING:
        raise HTTPException(
            status_code=409, 
            detail="Reddit ingestion is already running. Please wait for it to complete."
        )

    try:
        ingestion_status["reddit"] = CollectorStatus.RUNNING

        async def collect_reddit_data():
            try:
                # Initialize collector
                collector = RedditCollector()
                collector.db = get_mongodb_db()
                await collector.initialize()

                # Collect posts from specified subreddits
                all_posts = await collector.collect_trending_posts(
                    subreddits=request.sources, limit=request.limit or 100
                )

                logger.info(f"Collected {len(all_posts)} Reddit posts")

                # Store posts
                if all_posts:
                    await collector.store_posts(all_posts)
                    logger.info(f"Stored {len(all_posts)} Reddit posts in MongoDB")

                ingestion_status["reddit"] = CollectorStatus.IDLE
                return len(all_posts)

            except Exception as e:
                logger.exception(f"Reddit ingestion failed: {e}")
                ingestion_status["reddit"] = CollectorStatus.ERROR
                raise

        background_tasks.add_task(collect_reddit_data)

        return IngestionResponse(
            message=f"Reddit ingestion started for {len(request.sources)} subreddits",
            job_id=f"reddit_{hash(str(request.sources))}",
            status="started",
        )

    except Exception as e:
        ingestion_status["reddit"] = CollectorStatus.ERROR
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test", response_model=IngestionResponse)
async def test_ingestion(background_tasks: BackgroundTasks):
    """
    Test ingestion with default subreddits.
    """
    default_subreddits = ["python", "technology", "worldnews"]

    # Check if Reddit collector is already running
    if ingestion_status["reddit"] == CollectorStatus.RUNNING:
        raise HTTPException(
            status_code=409, 
            detail="Reddit ingestion is already running. Please wait for it to complete."
        )

    try:
        ingestion_status["reddit"] = CollectorStatus.RUNNING

        async def collect_test_data():
            try:
                collector = RedditCollector()
                collector.db = get_mongodb_db()
                await collector.initialize()

                # Collect from default subreddits
                posts = await collector.collect_trending_posts(
                    subreddits=default_subreddits, limit=10
                )

                logger.info(f"Test collected {len(posts)} Reddit posts")

                # Store posts
                if posts:
                    await collector.store_posts(posts)
                    logger.info(f"Test stored {len(posts)} Reddit posts")

                ingestion_status["reddit"] = CollectorStatus.IDLE
                return len(posts)

            except Exception as e:
                logger.exception(f"Test ingestion failed: {e}")
                ingestion_status["reddit"] = CollectorStatus.ERROR
                raise

        background_tasks.add_task(collect_test_data)

        return IngestionResponse(
            message=(f"Test ingestion started for: {', '.join(default_subreddits)}"),
            job_id="test_ingestion",
            status="started",
        )

    except Exception as e:
        ingestion_status["reddit"] = CollectorStatus.ERROR
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/data-summary", response_model=List[CollectedDataSummary])
async def get_data_summary():
    """
    Get summary of collected data in the database.
    """
    try:
        db = get_mongodb_db()
        collection = db.social_media_posts

        # Aggregate by platform
        pipeline = [
            {
                "$group": {
                    "_id": "$platform",
                    "count": {"$sum": 1},
                    "oldest": {"$min": "$created_utc"},
                    "newest": {"$max": "$created_utc"},
                    "topics": {"$push": "$topics"},
                }
            }
        ]

        results = await collection.aggregate(pipeline).to_list(None)

        summaries = []
        for result in results:
            # Flatten and deduplicate topics
            all_topics = []
            for topic_list in result.get("topics", []):
                if topic_list:
                    all_topics.extend(topic_list)
            unique_topics = list(set(all_topics))[:10]  # Limit to 10 topics

            summaries.append(
                CollectedDataSummary(
                    platform=result["_id"],
                    count=result["count"],
                    oldest=result.get("oldest"),
                    newest=result.get("newest"),
                    topics=unique_topics,
                )
            )

        return summaries

    except Exception as e:
        logger.exception(f"Error getting data summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
