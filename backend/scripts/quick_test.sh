#!/bin/bash
# Quick test script for agent-run endpoint

echo "🚀 Quorum AI Agent Test Runner"
echo "=============================="

# Check if backend is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ Backend is not running!"
    echo "   Please start it with: uv run main.py"
    exit 1
fi

echo "✅ Backend is running"

# Function to test a space
test_space() {
    local space_id=$1
    echo -e "\n🔍 Testing $space_id..."
    
    curl -X POST http://localhost:8000/agent-run \
        -H "Content-Type: application/json" \
        -d "{\"space_id\": \"$space_id\", \"dry_run\": true}" \
        -s | python3 -m json.tool
}

# Check command line arguments
if [ "$1" == "--help" ]; then
    echo -e "\nUsage:"
    echo "  ./quick_test.sh              # Test ENS DAO"
    echo "  ./quick_test.sh <space_id>   # Test specific space"
    echo "  ./quick_test.sh --all        # Test multiple spaces"
    echo -e "\nPopular spaces:"
    echo "  - ens.eth"
    echo "  - arbitrumfoundation.eth"
    echo "  - aave.eth"
    echo "  - gitcoindao.eth"
    echo "  - compound.eth"
    exit 0
elif [ "$1" == "--all" ]; then
    # Test multiple spaces
    for space in ens.eth arbitrumfoundation.eth aave.eth gitcoindao.eth compound.eth; do
        test_space $space
        sleep 2  # Be nice to the API
    done
elif [ -n "$1" ]; then
    # Test specific space
    test_space $1
else
    # Default: test ENS
    test_space "ens.eth"
fi

echo -e "\n✅ Test completed!"