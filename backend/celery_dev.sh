#!/bin/bash
# Development script to run Celery worker and beat in foreground for debugging

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Celery in Development Mode${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

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

# Create logs directory if it doesn't exist
mkdir -p logs

# Function to cleanup on exit
cleanup() {
    echo -e "\n${YELLOW}Shutting down Celery services...${NC}"
    # Kill the background processes
    kill $WORKER_PID $BEAT_PID 2>/dev/null
    wait $WORKER_PID $BEAT_PID 2>/dev/null
    echo -e "${GREEN}Celery services stopped${NC}"
    exit 0
}

# Set up trap to call cleanup on Ctrl+C
trap cleanup INT

# Start Celery worker in background
echo -e "${BLUE}Starting Celery worker...${NC}"
celery -A app.core.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=pipeline,scheduled,analysis \
    --hostname=worker@%h &
WORKER_PID=$!

# Give worker time to start
sleep 2

# Start Celery Beat in background
echo -e "${BLUE}Starting Celery Beat scheduler...${NC}"
celery -A app.core.celery_app beat \
    --loglevel=info &
BEAT_PID=$!

echo -e "${GREEN}Celery services are running!${NC}"
echo ""
echo -e "${YELLOW}Open another terminal to monitor with Flower:${NC}"
echo "  celery -A app.core.celery_app flower"
echo ""
echo -e "${YELLOW}Test the pipeline API:${NC}"
echo "  curl -X POST http://localhost:8000/api/v1/pipeline/trigger"
echo ""

# Wait for background processes
wait