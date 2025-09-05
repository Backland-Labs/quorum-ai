#!/bin/bash

echo "=== Executing Quorum AI Step 1 Test ==="
echo "Timestamp: $(date)"
echo "Working Directory: $(pwd)"

# Change to the project directory
cd /Users/max/code/quorum-ai

echo -e "\n1. Quick Health Check"
echo "Testing http://localhost:8716/health"

# Test if service is running
HEALTH_RESPONSE=$(curl -s --connect-timeout 3 --max-time 5 http://localhost:8716/health 2>/dev/null)
HEALTH_STATUS=$?

echo "Health check exit code: $HEALTH_STATUS"
echo "Health response: $HEALTH_RESPONSE"

if [ $HEALTH_STATUS -eq 0 ] && [ -n "$HEALTH_RESPONSE" ]; then
    echo "✅ Service is already running"
    SERVICE_RUNNING=true
else
    echo "❌ Service not running - starting it..."
    SERVICE_RUNNING=false

    # Start the backend service
    echo -e "\n2. Starting Backend Service"
    cd backend

    echo "Starting backend with: uv run main.py"
    uv run main.py &
    BACKEND_PID=$!

    echo "Backend started with PID: $BACKEND_PID"
    echo $BACKEND_PID > ../backend_test.pid

    echo "Waiting 20 seconds for service to initialize..."
    sleep 20

    # Test health again
    cd /Users/max/code/quorum-ai
    echo "Re-testing health endpoint..."

    HEALTH_RESPONSE=$(curl -s --connect-timeout 5 --max-time 10 http://localhost:8716/health 2>/dev/null)
    HEALTH_STATUS=$?

    echo "Health recheck exit code: $HEALTH_STATUS"
    echo "Health recheck response: $HEALTH_RESPONSE"

    if [ $HEALTH_STATUS -eq 0 ] && [ -n "$HEALTH_RESPONSE" ]; then
        echo "✅ Backend service started successfully"
        SERVICE_RUNNING=true
    else
        echo "❌ Backend service failed to start"
        SERVICE_RUNNING=false
    fi
fi

if [ "$SERVICE_RUNNING" = false ]; then
    echo "❌ STEP 1 FAILED: Cannot get service running"
    exit 1
fi

# Execute the agent run test
echo -e "\n3. Testing Agent Run Endpoint"
echo "Executing POST /agent-run with myshelldao.eth"

PAYLOAD='{"space_id": "myshelldao.eth", "dry_run": true}'
echo "Payload: $PAYLOAD"

echo "Making request..."
AGENT_RESPONSE=$(curl -X POST \
  http://localhost:8716/agent-run \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  --connect-timeout 10 \
  --max-time 180 \
  --silent \
  --show-error \
  2>&1)

AGENT_STATUS=$?

echo "Agent run exit code: $AGENT_STATUS"
echo "Response length: ${#AGENT_RESPONSE}"

if [ $AGENT_STATUS -eq 0 ]; then
    echo "✅ Agent run completed"
    echo "Response: $AGENT_RESPONSE"

    # Try to extract key info from JSON
    PROPOSALS=$(echo "$AGENT_RESPONSE" | grep -o '"proposals_analyzed":[0-9]*' | cut -d':' -f2)
    VOTES=$(echo "$AGENT_RESPONSE" | grep -o '"votes_cast":\[[^]]*\]' | grep -o '\[.*\]' | tr ',' '\n' | wc -l)

    echo "Proposals analyzed: $PROPOSALS"
    echo "Votes cast: $VOTES"

else
    echo "❌ Agent run failed"
    echo "Error output: $AGENT_RESPONSE"
fi

# Check logs for Snapshot evidence
echo -e "\n4. Checking Logs for Snapshot Evidence"

LOG_FILES=("backend/log.txt" "backend.log" "service.log")

for LOG_FILE in "${LOG_FILES[@]}"; do
    if [ -f "$LOG_FILE" ]; then
        echo "Checking $LOG_FILE..."

        SNAPSHOT_LINES=$(grep -i "snapshot\|graphql\|proposals" "$LOG_FILE" 2>/dev/null)
        if [ -n "$SNAPSHOT_LINES" ]; then
            echo "✅ Found Snapshot evidence in $LOG_FILE"
            echo "Sample entries:"
            echo "$SNAPSHOT_LINES" | tail -5
        else
            echo "⚠️ No Snapshot evidence in $LOG_FILE"
        fi
    else
        echo "Log file not found: $LOG_FILE"
    fi
done

echo -e "\n=== STEP 1 SUMMARY ==="
echo "Service Health: ✅"
if [ $AGENT_STATUS -eq 0 ]; then
    echo "Agent Run: ✅"
    echo "STEP 1 RESULT: ✅ PASSED"
    FINAL_STATUS=0
else
    echo "Agent Run: ❌"
    echo "STEP 1 RESULT: ❌ FAILED"
    FINAL_STATUS=1
fi

echo "Execution completed at: $(date)"

exit $FINAL_STATUS
