"""
Pipeline API endpoints for managing automated workflows.
"""

from __future__ import annotations

from typing import Any

from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException

from app.core.celery_app import celery_app
from app.core.logging import get_logger
from app.schemas.pipeline import (
    PipelineResponse,
    PipelineStatus,
    PipelineTriggerRequest,
    TaskStatus,
    URLAnalysisRequest,
)
from app.tasks.pipeline import analyze_url, run_full_pipeline
from app.tasks.scheduled import (
    cleanup_old_data,
    detect_emerging_trends,
    rescore_old_stories,
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("/trigger", response_model=PipelineResponse)
async def trigger_pipeline(request: PipelineTriggerRequest):
    """
    Trigger the full data processing pipeline.
    
    This will:
    1. Ingest data from specified sources
    2. Process posts into stories
    3. Calculate trust scores
    """
    try:
        # Start the pipeline
        task = run_full_pipeline.delay(subreddits=request.subreddits)

        return PipelineResponse(
            task_id=str(task.id),
            status="started",
            message=(
                f"Pipeline triggered for {len(request.subreddits or [])} subreddits"
            ),
        )

    except Exception as e:
        logger.exception("Failed to trigger pipeline")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-url", response_model=PipelineResponse)
async def analyze_news_url(request: URLAnalysisRequest):
    """
    Submit a URL for trustability analysis.
    
    This will:
    1. Extract content from the URL
    2. Search for related social media discussions
    3. Calculate trust score based on multiple factors
    """
    try:
        # Trigger URL analysis
        task = analyze_url.delay(url=request.url, user_id=request.user_id)

        return PipelineResponse(
            task_id=str(task.id),
            status="started",
            message=f"Analysis started for URL: {request.url}",
        )

    except Exception as e:
        logger.exception("Failed to analyze URL")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}", response_model=TaskStatus)
async def get_task_status(task_id: str):
    """Get the status of a pipeline task."""
    try:
        # Get task result
        result = AsyncResult(task_id, app=celery_app)

        status = result.status
        response: dict[str, Any] = {
            "task_id": task_id,
            "status": status,
        }

        if status == "PENDING":
            response["message"] = "Task is waiting to be processed"
        elif status == "STARTED":
            response["message"] = "Task is currently running"
            response["current"] = result.info.get("current", 0) if result.info else 0
            response["total"] = result.info.get("total", 100) if result.info else 100
        elif status == "SUCCESS":
            response["message"] = "Task completed successfully"
            response["result"] = result.result
        elif status == "FAILURE":
            response["message"] = f"Task failed: {result.info}"
            response["error"] = str(result.info)
        else:
            response["message"] = f"Unknown status: {status}"

        return TaskStatus(**response)

    except Exception as e:
        logger.exception("Failed to get task status")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status", response_model=PipelineStatus)
async def get_pipeline_status():
    """Get overall pipeline status and statistics."""
    try:
        # Get active tasks
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()

        # Count active tasks
        active_count = 0
        if active_tasks:
            for worker, tasks in active_tasks.items():
                active_count += len(tasks)

        # Count scheduled tasks
        scheduled_count = 0
        if scheduled_tasks:
            for worker, tasks in scheduled_tasks.items():
                scheduled_count += len(tasks)

        # Get worker status
        stats = inspect.stats()
        workers_online = len(stats) if stats else 0

        return PipelineStatus(
            workers_online=workers_online,
            active_tasks=active_count,
            scheduled_tasks=scheduled_count,
            pipeline_enabled=workers_online > 0,
        )

    except Exception:
        logger.exception("Failed to get pipeline status")
        # Return degraded status if Celery is not available
        return PipelineStatus(
            workers_online=0,
            active_tasks=0,
            scheduled_tasks=0,
            pipeline_enabled=False,
        )


@router.post("/maintenance/cleanup")
async def trigger_cleanup():
    """Manually trigger database cleanup task."""
    try:
        task = cleanup_old_data.delay()

        return PipelineResponse(
            task_id=str(task.id),
            status="started",
            message="Database cleanup started",
        )

    except Exception as e:
        logger.exception("Failed to trigger cleanup")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/maintenance/rescore")
async def trigger_rescoring():
    """Manually trigger trust score recalculation for old stories."""
    try:
        task = rescore_old_stories.delay()

        return PipelineResponse(
            task_id=str(task.id),
            status="started",
            message="Story re-scoring started",
        )

    except Exception as e:
        logger.exception("Failed to trigger re-scoring")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trends/detect")
async def trigger_trend_detection():
    """Manually trigger trend detection."""
    try:
        task = detect_emerging_trends.delay()

        return PipelineResponse(
            task_id=str(task.id),
            status="started",
            message="Trend detection started",
        )

    except Exception as e:
        logger.exception("Failed to trigger trend detection")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/cancel/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a running task."""
    try:
        result = AsyncResult(task_id, app=celery_app)
        result.revoke(terminate=True)

        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancellation requested",
        }

    except Exception as e:
        logger.exception("Failed to cancel task")
        raise HTTPException(status_code=500, detail=str(e))
