# Veracity Pipeline Orchestration

The automated pipeline system connects data ingestion, story processing, and trust scoring into a seamless workflow.

## Architecture Overview

```
Data Sources → Ingestion → Processing → Trust Scoring → Display
     ↑                                                        ↓
     └──────────── Scheduled/User Triggers ──────────────────┘
```

## Components

### 1. Celery Task Queue
- **Worker**: Executes pipeline tasks
- **Beat**: Schedules periodic tasks
- **Flower**: Web-based monitoring dashboard (http://localhost:5555)

### 2. Pipeline Tasks

#### Ingestion Tasks
- `pipeline.ingest_reddit` - Collect Reddit posts from specified subreddits
- Automatically triggers processing when complete

#### Processing Tasks
- `pipeline.process_posts` - Convert raw posts to structured stories
- Deduplicates content and calculates initial metrics
- Automatically triggers trust scoring

#### Scoring Tasks
- `pipeline.score_trust` - Calculate comprehensive trust scores
- Updates stories with credibility ratings
- Sends real-time WebSocket updates

### 3. Scheduled Tasks (via Celery Beat)

| Task | Schedule | Description |
|------|----------|-------------|
| Reddit Ingestion | Every 15 min | Collect posts from monitored subreddits |
| Post Processing | Every 10 min | Process new posts into stories |
| Trust Scoring | Every 5 min | Update trust scores for stories |
| Data Cleanup | Daily at 3 AM | Remove old/low-value data |

## Quick Start

### Development Setup

1. **Start infrastructure services:**
```bash
podman-compose up -d
```

2. **Install dependencies:**
```bash
cd backend
source .venv/bin/activate
pip install -e .  # Installs with new Celery dependencies
```

3. **Start Celery in development mode:**
```bash
cd backend
./celery_dev.sh  # Runs worker and beat in foreground
```

4. **Start the backend API:**
```bash
cd backend
python -m app.main
```

5. **Monitor with Flower (optional):**
```bash
celery -A app.core.celery_app flower
# Access at http://localhost:5555
```

### Production Deployment

```bash
# Start all services including Celery
docker-compose -f docker-compose.yml -f docker-compose.celery.yml up -d
```

## API Endpoints

### Pipeline Control

#### Trigger Full Pipeline
```bash
POST /api/v1/pipeline/trigger
{
  "subreddits": ["worldnews", "technology"],
  "limit": 100
}
```

#### Analyze URL
```bash
POST /api/v1/pipeline/analyze-url
{
  "url": "https://example.com/article",
  "user_id": "optional-user-id"
}
```

#### Check Task Status
```bash
GET /api/v1/pipeline/status/{task_id}
```

#### Get Pipeline Status
```bash
GET /api/v1/pipeline/status
```

### Manual Triggers

#### Trigger Cleanup
```bash
POST /api/v1/pipeline/maintenance/cleanup
```

#### Trigger Re-scoring
```bash
POST /api/v1/pipeline/maintenance/rescore
```

#### Detect Trends
```bash
POST /api/v1/pipeline/trends/detect
```

## Workflow Examples

### Automatic Pipeline (Scheduled)
1. Every 15 minutes: Reddit ingestion runs automatically
2. When ingestion completes → Post processing starts
3. When processing completes → Trust scoring starts
4. WebSocket updates sent to connected clients

### User-Triggered Analysis
```python
# User submits URL for analysis
response = requests.post(
    "http://localhost:8000/api/v1/pipeline/analyze-url",
    json={"url": "https://news-site.com/article"}
)
task_id = response.json()["task_id"]

# Check status
status = requests.get(
    f"http://localhost:8000/api/v1/pipeline/status/{task_id}"
)
print(status.json())
```

### Manual Pipeline Trigger
```python
# Trigger full pipeline for specific subreddits
response = requests.post(
    "http://localhost:8000/api/v1/pipeline/trigger",
    json={
        "subreddits": ["worldnews", "politics", "science"],
        "limit": 50
    }
)
```

## Monitoring

### Celery Flower Dashboard
Access at http://localhost:5555 when running:
- Active tasks
- Task history
- Worker status
- Queue lengths
- Performance metrics

### Logs
```bash
# Worker logs
tail -f backend/logs/celery_worker.log

# Beat scheduler logs
tail -f backend/logs/celery_beat.log

# API logs
tail -f backend/logs/api.log
```

### Health Checks
```bash
# Check if workers are responding
celery -A app.core.celery_app inspect ping

# List active tasks
celery -A app.core.celery_app inspect active

# List scheduled tasks
celery -A app.core.celery_app inspect scheduled
```

## Configuration

### Environment Variables
Add to `.env`:
```env
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Pipeline Configuration
TREND_DETECTION_WINDOW_MINUTES=60
TRUST_SCORE_UPDATE_INTERVAL_MINUTES=15
MAX_POSTS_PER_BATCH=1000
```

### Customizing Schedules
Edit `backend/app/core/celery_app.py`:
```python
celery_app.conf.beat_schedule = {
    "ingest-reddit-periodic": {
        "task": "scheduled.reddit_ingestion",
        "schedule": crontab(minute="*/15"),  # Change frequency
    },
    # Add more scheduled tasks...
}
```

## Troubleshooting

### Common Issues

#### Redis Connection Error
```bash
# Check Redis is running
podman ps | grep redis
# or
redis-cli ping
```

#### Workers Not Processing Tasks
```bash
# Restart Celery workers
cd backend
./stop_celery.sh
./start_celery.sh
```

#### Tasks Stuck in Queue
```bash
# Purge all queues (WARNING: loses pending tasks)
celery -A app.core.celery_app purge -f
```

#### Memory Issues
Adjust worker concurrency in `celery_dev.sh`:
```bash
--concurrency=2  # Reduce for less memory usage
```

## Performance Tuning

### Worker Configuration
- **Concurrency**: Number of worker processes (default: 4)
- **Prefetch Multiplier**: Tasks pre-loaded per worker (default: 2)
- **Max Tasks Per Child**: Worker restart frequency (default: 100)

### Queue Priorities
Tasks are routed to different queues:
- `pipeline`: Main data processing tasks
- `scheduled`: Periodic scheduled tasks
- `analysis`: Heavy analysis tasks

### Rate Limiting
API calls are rate-limited to respect external services:
```python
"app.tasks.pipeline.ingest_social_media": {
    "rate_limit": "1/m",  # 1 per minute
}
```

## Next Steps

After the pipeline is running:
1. Monitor ingestion rates and adjust schedules
2. Fine-tune trust scoring algorithms
3. Add more data sources (Twitter, news APIs)
4. Implement URL analysis with article extraction
5. Add user preference learning