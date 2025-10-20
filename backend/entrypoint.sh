#!/bin/bash
set -e

# Function to handle SIGTERM gracefully
cleanup() {
    echo "Received signal, shutting down gracefully..."
    if [ -n "$MAIN_PID" ]; then
        kill -TERM "$MAIN_PID" 2>/dev/null || true
        wait "$MAIN_PID"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT SIGQUIT

# Environment variable setup
export PYTHONUNBUFFERED=1
export PYTHONPATH=/app:$PYTHONPATH

# Create logs directory if it doesn't exist
mkdir -p /app/logs

# Set secure permissions for ethereum private key file if it exists
if [ -f "/agent_key/ethereum_private_key.txt" ]; then
    chmod 600 /agent_key/ethereum_private_key.txt
    echo "Set secure permissions (600) for /agent_key/ethereum_private_key.txt"
elif [ -f "/app/ethereum_private_key.txt" ]; then
    chmod 600 /app/ethereum_private_key.txt
    echo "Set secure permissions (600) for /app/ethereum_private_key.txt"
fi

# Setup checkpoint service with 24-hour delay
if [ -f "/app/scripts/checkpoint.py" ]; then
    echo "================================"
    echo "Setting up checkpoint service"
    echo "================================"

    # Calculate time 24 hours from now
    FUTURE_MINUTE=$(date -d "+24 hours" +%M)
    FUTURE_HOUR=$(date -d "+24 hours" +%H)

    # Create dynamic crontab to run daily at this time
    echo "$FUTURE_MINUTE $FUTURE_HOUR * * * cd /app && timeout 300 uv run --quiet --script scripts/checkpoint.py >> /app/logs/checkpoint.log 2>&1" | crontab -

    # Start cron daemon
    service cron start

    # Log the schedule
    FIRST_RUN=$(date -d "+24 hours" '+%Y-%m-%d %H:%M:%S %Z')
    echo "✓ Checkpoint configured"
    echo "================================"
fi

# Setup agent-run service with 1-hour delay
if [ -f "/app/scripts/trigger_agent_run.py" ]; then
    echo "================================"
    echo "Setting up agent-run service"
    echo "================================"

    # Calculate time 1 hour from now
    AGENT_MINUTE=$(date -d "+1 hour" +%M)
    AGENT_HOUR=$(date -d "+1 hour" +%H)

    # Append to existing crontab to run daily at this time
    (crontab -l 2>/dev/null; echo "$AGENT_MINUTE $AGENT_HOUR * * * cd /app && timeout 300 uv run --quiet --script scripts/trigger_agent_run.py") | crontab -

    # Log the schedule
    AGENT_FIRST_RUN=$(date -d "+1 hour" '+%Y-%m-%d %H:%M:%S %Z')
    echo "✓ Agent-run configured"
    echo "  First run: $AGENT_FIRST_RUN"
    echo "  Schedule: Daily at ${AGENT_HOUR}:${AGENT_MINUTE} UTC"
    echo "================================"
fi

echo "Starting Quorum AI application..."
echo "Environment: $(printenv | grep -E '^(DEBUG|HOST|HEALTH_CHECK_PORT)=' || echo 'No relevant env vars set')"

# Start the main application in the background
uv run --no-sync python -O main.py &
MAIN_PID=$!

echo "Application started with PID: $MAIN_PID"

# Wait for the background process to complete
wait "$MAIN_PID"
