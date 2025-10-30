#!/bin/bash
set -e

# Function to handle SIGTERM gracefully
cleanup() {
    echo "Received signal, shutting down gracefully..."
    if [ -n "$SUPERCRONIC_PID" ]; then
        kill -TERM "$SUPERCRONIC_PID" 2>/dev/null || true
        wait "$SUPERCRONIC_PID" 2>/dev/null || true
    fi
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

# Setup scheduled jobs using supercronic
if [ -f "/app/scripts/checkpoint.py" ] || [ -f "/app/scripts/trigger_agent_run.py" ]; then
    echo "================================"
    echo "Setting up scheduled jobs (supercronic)"
    echo "================================"

    # Log current user information for debugging
    echo "Current UID: $(id -u), GID: $(id -g), User: $(whoami 2>&1 || echo 'unknown')"

    # Create crontab file
    CRON_FILE="/app/schedules.cron"
    echo "CRON_TZ=UTC" > "$CRON_FILE"

    # Setup checkpoint service with 24-hour delay
    if [ -f "/app/scripts/checkpoint.py" ]; then
        # Calculate time 24 hours from now
        FUTURE_MINUTE=$(date -d "+24 hours" +%M)
        FUTURE_HOUR=$(date -d "+24 hours" +%H)
        
        echo "$FUTURE_MINUTE $FUTURE_HOUR * * * cd /app && timeout 300 uv run --quiet --script scripts/checkpoint.py >> /app/logs/checkpoint.log 2>&1" >> "$CRON_FILE"
        
        FIRST_RUN=$(date -d "+24 hours" '+%Y-%m-%d %H:%M:%S %Z')
        echo "Checkpoint schedule: Daily at ${FUTURE_HOUR}:${FUTURE_MINUTE} UTC"
        echo "First checkpoint run: $FIRST_RUN"
    fi

    # Setup agent-run service with 5-minute delay
    if [ -f "/app/scripts/trigger_agent_run.py" ]; then
        # Calculate time 5 minutes from now
        AGENT_MINUTE=$(date -d "+5 minutes" +%M)
        AGENT_HOUR=$(date -d "+5 minutes" +%H)
        
        echo "$AGENT_MINUTE $AGENT_HOUR * * * cd /app && timeout 300 uv run --quiet --script scripts/trigger_agent_run.py >> /app/logs/agent_run.log 2>&1" >> "$CRON_FILE"
        
        AGENT_FIRST_RUN=$(date -d "+5 minutes" '+%Y-%m-%d %H:%M:%S %Z')
        echo "Agent-run schedule: Daily at ${AGENT_HOUR}:${AGENT_MINUTE} UTC"
        echo "First agent-run: $AGENT_FIRST_RUN"
    fi

    # Display crontab contents
    echo ""
    echo "Crontab contents:"
    sed 's/^/  /' "$CRON_FILE"

    # Test and start supercronic
    echo ""
    echo "Starting supercronic..."
    if /usr/local/bin/supercronic -test "$CRON_FILE" >/dev/null 2>&1; then
        /usr/local/bin/supercronic "$CRON_FILE" &
        SUPERCRONIC_PID=$!
        echo "✓ supercronic started with PID: $SUPERCRONIC_PID"
    else
        echo "✗ Invalid crontab; supercronic not started"
    fi
    
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
