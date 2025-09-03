#!/bin/bash

# Change to the project directory
cd /Users/max/code/quorum-ai

echo "=== Starting Quorum AI Test Execution ==="
echo "Timestamp: $(date)"

# Step 1: Check if service is running
echo -e "\n1. Testing service health..."
python3 test_health_check.py

HEALTH_STATUS=$?

if [ $HEALTH_STATUS -ne 0 ]; then
    echo -e "\n❌ Service not running. Starting services..."
    
    # Start services using the startup script
    echo "Starting services with startup script..."
    chmod +x startup.sh
    ./startup.sh --claude-code
    
    # Wait for services to be ready
    echo "Waiting 10 seconds for services to initialize..."
    sleep 10
    
    # Test health again
    echo "Re-testing service health..."
    python3 test_health_check.py
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to start services. Exiting."
        exit 1
    fi
fi

# Step 2: Execute agent run test
echo -e "\n2. Executing agent run test..."
python3 test_agent_run.py

# Save the output to our evidence file
python3 test_agent_run.py >> test_step1_snapshot_queries.md

echo -e "\n=== Test execution completed ==="