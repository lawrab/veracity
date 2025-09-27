"""
Celery application configuration for task queue and scheduling.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Create Celery instance
celery_app = Celery(
    "veracity",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.pipeline", "app.tasks.scheduled"],
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,  # Results expire after 1 hour
    task_track_started=True,
    task_time_limit=600,  # 10 minutes hard limit
    task_soft_time_limit=540,  # 9 minutes soft limit
    worker_prefetch_multiplier=2,
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks to prevent memory leaks
)

# Configure scheduled tasks with Celery Beat
celery_app.conf.beat_schedule = {
    # Ingest Reddit data every 15 minutes
    "ingest-reddit-periodic": {
        "task": "app.tasks.scheduled.scheduled_reddit_ingestion",
        "schedule": crontab(minute="*/15"),
        "args": (),
    },
    # Process posts to stories every 10 minutes
    "process-posts-periodic": {
        "task": "app.tasks.scheduled.scheduled_post_processing",
        "schedule": crontab(minute="*/10"),
        "args": (),
    },
    # Update trust scores every 5 minutes
    "update-trust-scores": {
        "task": "app.tasks.scheduled.scheduled_trust_scoring",
        "schedule": crontab(minute="*/5"),
        "args": (),
    },
    # Cleanup old data daily at 3 AM
    "cleanup-old-data": {
        "task": "app.tasks.scheduled.cleanup_old_data",
        "schedule": crontab(hour=3, minute=0),
        "args": (),
    },
}

# Task routing for different queues
celery_app.conf.task_routes = {
    "app.tasks.pipeline.*": {"queue": "pipeline"},
    "app.tasks.scheduled.*": {"queue": "scheduled"},
    "app.tasks.analysis.*": {"queue": "analysis"},
}

# Retry configuration
celery_app.conf.task_annotations = {
    "*": {
        "rate_limit": "10/s",
        "max_retries": 3,
        "default_retry_delay": 60,  # 1 minute
    },
    "app.tasks.pipeline.ingest_social_media": {
        "rate_limit": "1/m",  # Respect API rate limits
        "max_retries": 5,
    },
}