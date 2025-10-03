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
if [ -f "/app/ethereum_private_key.txt" ]; then
    chmod 600 /app/ethereum_private_key.txt
    echo "Set secure permissions (600) for ethereum_private_key.txt"
fi

echo "Starting Quorum AI application..."
echo "Environment: $(printenv | grep -E '^(DEBUG|HOST|HEALTH_CHECK_PORT)=' || echo 'No relevant env vars set')"

# Start the main application in the background
uv run --no-sync python -O main.py &
MAIN_PID=$!

echo "Application started with PID: $MAIN_PID"

# Wait for the background process to complete
wait "$MAIN_PID"
