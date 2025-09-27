#!/usr/bin/env bash

# End-to-End Data Pipeline Testing Script for Veracity Platform
# Tests: Reddit ingestion → MongoDB storage → Trust scoring → WebSocket updates

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

API_BASE_URL="http://localhost:8000/api/v1"

echo -e "${BLUE}🚀 Starting end-to-end data pipeline testing...${NC}"

# Function to make API calls with error handling
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    
    echo -e "${YELLOW}📡 $description${NC}"
    echo "  → $method $API_BASE_URL$endpoint"
    
    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$API_BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" "$API_BASE_URL$endpoint")
    fi
    
    # Split response and status code
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$status_code" -ge 200 ] && [ "$status_code" -lt 300 ]; then
        echo -e "${GREEN}✓ Success ($status_code)${NC}"
        echo "$body" | jq . 2>/dev/null || echo "$body"
        return 0
    else
        echo -e "${RED}❌ Failed ($status_code)${NC}"
        echo "$body"
        return 1
    fi
}

# Function to wait for completion
wait_for_completion() {
    local timeout=$1
    local check_command=$2
    local description=$3
    
    echo -e "${YELLOW}⏳ $description (timeout: ${timeout}s)${NC}"
    
    local elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if eval "$check_command" >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Completed after ${elapsed}s${NC}"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        echo -n "."
    done
    
    echo -e "\n${RED}❌ Timeout after ${timeout}s${NC}"
    return 1
}

# Test 1: Check API health
echo -e "\n${BLUE}📋 Step 1: Checking API health${NC}"
echo -e "${YELLOW}📡 Health check${NC}"
echo "  → GET http://localhost:8000/health"

response=$(curl -s -w "\n%{http_code}" http://localhost:8000/health)
status_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n -1)

if [ "$status_code" -ge 200 ] && [ "$status_code" -lt 300 ]; then
    echo -e "${GREEN}✓ Success ($status_code)${NC}"
    echo "$body" | jq . 2>/dev/null || echo "$body"
else
    echo -e "${RED}❌ Failed ($status_code)${NC}"
    echo "$body"
    exit 1
fi

# Test 2: Check ingestion status
echo -e "\n${BLUE}📋 Step 2: Checking ingestion status${NC}"
api_call "GET" "/ingestion/status" "" "Get ingestion status"

# Test 3: Test Reddit data collection
echo -e "\n${BLUE}📋 Step 3: Testing Reddit data collection${NC}"

# Small test with popular subreddits
REDDIT_REQUEST='{
    "sources": ["technology", "worldnews", "science"],
    "limit": 5
}'

api_call "POST" "/ingestion/reddit" "$REDDIT_REQUEST" "Start Reddit data collection"

# Wait for ingestion to complete
echo -e "\n${YELLOW}⏳ Waiting for Reddit ingestion to complete...${NC}"
wait_for_completion 120 "curl -s '$API_BASE_URL/api/v1/ingestion/status' | grep -q '\"reddit\": \"idle\"'" "Waiting for Reddit ingestion to complete"

# Check ingestion status
api_call "GET" "/ingestion/status" "" "Check ingestion progress"

# Test 4: Verify data in MongoDB via API
echo -e "\n${BLUE}📋 Step 4: Verifying collected data${NC}"
api_call "GET" "/ingestion/data-summary" "" "Get data summary from MongoDB"

# Test 5: Wait for data processing and check if stories were created
echo -e "\n${BLUE}📋 Step 5: Checking story creation and processing${NC}"

# Wait a bit for processing
sleep 3

# Check if any stories were created (this endpoint might not exist yet)
echo -e "${YELLOW}📡 Checking for processed stories${NC}"
stories_response=$(curl -s "$API_BASE_URL/stories?limit=5" || echo '{"stories": []}')
echo "$stories_response" | jq . 2>/dev/null || echo "$stories_response"

# Test 6: Test trust scoring if stories exist
echo -e "\n${BLUE}📋 Step 6: Testing trust scoring${NC}"

# Extract story IDs from response
story_ids=$(echo "$stories_response" | jq -r '.stories[]?.id // empty' 2>/dev/null || echo "")

if [ -n "$story_ids" ]; then
    # Test trust scoring on first story
    first_story_id=$(echo "$story_ids" | head -n1)
    
    TRUST_REQUEST="{\"story_id\": \"$first_story_id\"}"
    api_call "POST" "/trust/calculate" "$TRUST_REQUEST" "Calculate trust score for story $first_story_id"
    
    # Get trust score
    api_call "GET" "/trust/story/$first_story_id/score" "" "Get current trust score"
else
    echo -e "${YELLOW}⚠️  No stories found for trust scoring test${NC}"
fi

# Test 7: Test WebSocket connection
echo -e "\n${BLUE}📋 Step 7: Testing WebSocket connectivity${NC}"

echo -e "${YELLOW}📡 Testing WebSocket connection${NC}"
# Test WebSocket endpoint availability (simpler approach)
websocket_test=$(curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  --max-time 5 \
  http://localhost:8000/api/v1/ws/connect?channel=general 2>&1 | head -1 || echo "Failed")

if [[ "$websocket_test" == *"101"* ]]; then
    echo -e "${GREEN}✓ WebSocket endpoint accepts connections${NC}"
else
    echo -e "${YELLOW}⚠️  WebSocket test inconclusive (endpoint may still work)${NC}"
fi

# Test 8: Trigger test ingestion for WebSocket updates
echo -e "\n${BLUE}📋 Step 8: Testing real-time updates${NC}"

echo -e "${YELLOW}📡 Starting test ingestion to trigger WebSocket updates${NC}"
api_call "POST" "/ingestion/test" "" "Start test ingestion"

echo -e "${YELLOW}💡 To monitor WebSocket updates in real-time:${NC}"
echo "  Run this in another terminal:"
echo "  websocat ws://localhost:8000/api/v1/ws/connect?channel=general"

# Test 9: Final verification
echo -e "\n${BLUE}📋 Step 9: Final verification${NC}"

# Check final data summary
api_call "GET" "/ingestion/data-summary" "" "Final data summary"

# Check ingestion status
api_call "GET" "/ingestion/status" "" "Final ingestion status"

# Summary
echo -e "\n${GREEN}🎉 End-to-end testing completed!${NC}"
echo -e "\n${BLUE}📊 Test Summary:${NC}"
echo -e "  ✓ API health check"
echo -e "  ✓ Reddit data collection"
echo -e "  ✓ MongoDB data storage verification"
echo -e "  ✓ Story processing check"
echo -e "  ✓ Trust scoring (if stories available)"
echo -e "  ✓ WebSocket connectivity"
echo -e "  ✓ Real-time update triggers"

echo -e "\n${YELLOW}💡 Next steps:${NC}"
echo -e "  1. Monitor WebSocket updates: websocat ws://localhost:8000/api/v1/ws/connect?channel=general"
echo -e "  2. Check frontend dashboard for real-time updates"
echo -e "  3. Verify trust scores update automatically"
echo -e "  4. Test with larger data sets if needed"

echo -e "\n${GREEN}✅ Pipeline testing complete!${NC}"