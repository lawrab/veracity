#!/usr/bin/env bash
# Script to stop Celery worker and beat scheduler

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Stopping Veracity Celery Workers${NC}"

# Stop Celery worker
if [ -f celery_worker.pid ]; then
    PID=$(cat celery_worker.pid)
    if kill $PID 2>/dev/null; then
        echo -e "${GREEN}✓ Celery worker stopped (PID: $PID)${NC}"
        rm celery_worker.pid
    else
        echo -e "${YELLOW}Worker process not found, removing stale PID file${NC}"
        rm celery_worker.pid
    fi
else
    echo -e "${YELLOW}No worker PID file found${NC}"
fi

# Stop Celery Beat
if [ -f celery_beat.pid ]; then
    PID=$(cat celery_beat.pid)
    if kill $PID 2>/dev/null; then
        echo -e "${GREEN}✓ Celery Beat stopped (PID: $PID)${NC}"
        rm celery_beat.pid
    else
        echo -e "${YELLOW}Beat process not found, removing stale PID file${NC}"
        rm celery_beat.pid
    fi
else
    echo -e "${YELLOW}No beat PID file found${NC}"
fi

# Clean up any schedule database
if [ -f celerybeat-schedule ]; then
    rm celerybeat-schedule
    echo -e "${GREEN}✓ Removed beat schedule database${NC}"
fi

echo -e "${GREEN}All Celery services stopped${NC}"