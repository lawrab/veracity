#!/bin/bash
# Script to start Celery worker and beat scheduler

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Veracity Celery Workers${NC}"

# Check if Redis is running
if ! nc -z localhost 6379 2>/dev/null; then
    echo -e "${RED}Error: Redis is not running on localhost:6379${NC}"
    echo "Please start Redis first with: podman-compose up -d redis"
    exit 1
fi

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "../.venv/bin/activate" ]; then
    source ../.venv/bin/activate
else
    echo -e "${YELLOW}Warning: Virtual environment not found${NC}"
fi

# Start Celery worker in the background
echo -e "${GREEN}Starting Celery worker...${NC}"
celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --queues=pipeline,scheduled,analysis \
    --hostname=worker@%h \
    --detach \
    --pidfile=celery_worker.pid \
    --logfile=logs/celery_worker.log

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Celery worker started${NC}"
else
    echo -e "${RED}✗ Failed to start Celery worker${NC}"
    exit 1
fi

# Start Celery Beat scheduler in the background
echo -e "${GREEN}Starting Celery Beat scheduler...${NC}"
celery -A app.core.celery_app beat \
    --loglevel=info \
    --detach \
    --pidfile=celery_beat.pid \
    --logfile=logs/celery_beat.log

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Celery Beat scheduler started${NC}"
else
    echo -e "${RED}✗ Failed to start Celery Beat${NC}"
    # Stop worker if beat fails
    if [ -f celery_worker.pid ]; then
        kill $(cat celery_worker.pid)
        rm celery_worker.pid
    fi
    exit 1
fi

echo -e "${GREEN}All Celery services started successfully!${NC}"
echo ""
echo "Monitor logs with:"
echo "  tail -f logs/celery_worker.log"
echo "  tail -f logs/celery_beat.log"
echo ""
echo "Stop services with:"
echo "  ./stop_celery.sh"
echo ""
echo "Monitor tasks with Flower (if installed):"
echo "  celery -A app.core.celery_app flower"