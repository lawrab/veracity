"""
Processing API endpoints for converting raw posts to stories.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_mongodb_db, get_postgres_session
from app.core.logging import get_logger
from app.schemas.story import StoryCreate
from app.services.story_service import StoryService

logger = get_logger(__name__)

router = APIRouter()


@router.post("/process-posts")
async def process_posts_to_stories(
    background_tasks: BackgroundTasks,
    limit: int = 50,
    db: AsyncSession = Depends(get_postgres_session),
):
    """
    Process raw social media posts into structured stories.
    """
    try:

        async def process_posts():
            try:
                # Get MongoDB client
                mongo_db = get_mongodb_db()
                collection = mongo_db.social_media_posts

                # Get recent posts that haven't been processed
                posts = await collection.find({}).limit(limit).to_list(length=limit)

                if not posts:
                    logger.info("No posts found to process")
                    return

                logger.info(f"Processing {len(posts)} posts into stories")

                # Group posts by similar content/topics to create stories
                story_service = StoryService(db)
                stories_created = 0

                for post in posts:
                    try:
                        # Create a story from the post
                        title = post.get("title", post.get("content", "Untitled"))[:200]
                        score = post.get("score", 0)
                        comments = post.get("num_comments", 1)
                        velocity = score / max(1, comments)
                        story_data = StoryCreate(
                            title=title,
                            description=post.get("content", ""),
                            category=post.get("subreddit", "general"),
                            trust_score=50.0,  # Default neutral score
                            velocity=velocity,
                            first_seen_at=datetime.fromtimestamp(
                                post.get("created_utc", datetime.utcnow().timestamp()),
                                tz=timezone.utc,
                            ),
                        )

                        await story_service.create_story(story_data)
                        stories_created += 1

                    except Exception as e:
                        logger.exception(
                            "Failed to create story from post %s: %s", post.get("id"), e
                        )
                        continue

                logger.info("Successfully created %d stories", stories_created)

            except Exception as e:
                logger.exception(f"Post processing failed: {e}")
                raise

        background_tasks.add_task(process_posts)

        return {
            "message": f"Started processing up to {limit} posts into stories",
            "status": "started",
        }

    except Exception as e:
        logger.exception(f"Failed to start post processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/processing-status")
async def get_processing_status():
    """
    Get status of story processing pipeline.
    """
    try:
        # Get counts from both databases
        mongo_db = get_mongodb_db()
        posts_collection = mongo_db.social_media_posts

        total_posts = await posts_collection.count_documents({})

        # This would be enhanced to track processing status in Redis
        # For now, return basic counts
        return {
            "total_posts": total_posts,
            "processing_status": "idle",
            "last_processed": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.exception(f"Failed to get processing status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
