#!/bin/bash
# Test script to verify supercronic works with UID 501 (Olas constraint)

set -e

echo "================================"
echo "Building test image..."
echo "================================"
docker build -t quorum-ai-supercronic-test .

echo ""
echo "================================"
echo "Testing with UID 501 (Olas mode)"
echo "================================"

# Create minimal test environment
TEST_DIR=$(mktemp -d)
echo "Test directory: $TEST_DIR"

# Create minimal config files
cat > "$TEST_DIR/ethereum_private_key.txt" << 'EOF'
0000000000000000000000000000000000000000000000000000000000000001
EOF

cat > "$TEST_DIR/.env.test" << 'EOF'
DEBUG=true
HEALTH_CHECK_PORT=8716
BASE_LEDGER_RPC=https://base-rpc.publicnode.com
EOF

# Run container as UID 501 (like Olas)
echo ""
echo "Starting container as UID 501:20..."
CONTAINER_ID=$(docker run -d --rm \
    --user 501:20 \
    -v "$TEST_DIR/ethereum_private_key.txt:/agent_key/ethereum_private_key.txt" \
    --env-file "$TEST_DIR/.env.test" \
    quorum-ai-supercronic-test)

CONTAINER_PID=$$
echo "Container started with PID: $CONTAINER_PID"

# Wait for startup (30 seconds)
echo ""
echo "Waiting 30 seconds for startup..."
sleep 30

# Check if container is still running
if docker ps -q --no-trunc | grep -q "$CONTAINER_ID"; then
    echo "✓ Container is running"
    
    # Get container logs
    echo ""
    echo "================================"
    echo "Container startup logs:"
    echo "================================"
    docker logs "$CONTAINER_ID" 2>&1 | grep -A 20 "Setting up scheduled jobs"
    
    # Kill container
    docker stop "$CONTAINER_ID" >/dev/null 2>&1
    
    echo ""
    echo "✓ Test completed successfully"
else
    echo "✗ Container crashed during startup"
    docker logs "$CONTAINER_ID" 2>&1 | tail -50
    exit 1
fi

# Cleanup
rm -rf "$TEST_DIR"
echo ""
echo "Cleaned up test directory"
