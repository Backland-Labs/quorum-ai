#!/bin/bash
# Script to run Attestation Tracker CI tests locally
# This mimics the GitHub Action workflow for local development

set -e  # Exit on error

echo "=================================================="
echo "Attestation Tracker CI - Local Test Runner"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "Checking prerequisites..."

# Check if Foundry is installed
if ! command -v forge &> /dev/null; then
    echo -e "${RED}❌ Foundry (forge) is not installed${NC}"
    echo "Install it from: https://book.getfoundry.sh/getting-started/installation"
    exit 1
fi

# Check if Anvil is installed
if ! command -v anvil &> /dev/null; then
    echo -e "${RED}❌ Anvil is not installed${NC}"
    echo "Install it from: https://book.getfoundry.sh/getting-started/installation"
    exit 1
fi

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}⚠️  UV is not installed, installing...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

echo -e "${GREEN}✅ All prerequisites met${NC}"
echo ""

# Parse command line arguments
SKIP_BUILD=false
KEEP_ANVIL=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --keep-anvil)
            KEEP_ANVIL=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --skip-build    Skip contract compilation"
            echo "  --keep-anvil    Keep Anvil running after tests"
            echo "  --verbose       Enable verbose output"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Build contracts if not skipping
if [ "$SKIP_BUILD" = false ]; then
    echo "Building contracts..."
    cd contracts
    forge build
    cd ..
    echo -e "${GREEN}✅ Contracts built successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Skipping contract build${NC}"
fi
echo ""

# Check if Anvil is already running
if lsof -Pi :8545 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port 8545 is already in use. Stopping existing process...${NC}"
    lsof -Pi :8545 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start Anvil
echo "Starting Anvil with Base mainnet fork..."
if [ "$VERBOSE" = true ]; then
    anvil --fork-url https://mainnet.base.org --auto-impersonate &
else
    anvil --fork-url https://mainnet.base.org --auto-impersonate --silent &
fi
ANVIL_PID=$!

# Function to cleanup on exit
cleanup() {
    if [ "$KEEP_ANVIL" = false ] && [ ! -z "$ANVIL_PID" ]; then
        echo ""
        echo "Stopping Anvil..."
        kill $ANVIL_PID 2>/dev/null || true
    elif [ "$KEEP_ANVIL" = true ]; then
        echo ""
        echo -e "${YELLOW}ℹ️  Anvil still running on PID: $ANVIL_PID${NC}"
        echo "To stop it manually: kill $ANVIL_PID"
    fi
}

# Set up cleanup trap
trap cleanup EXIT

# Wait for Anvil to be ready
echo "Waiting for Anvil to start..."
for i in {1..30}; do
    if curl -s http://localhost:8545 > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Anvil is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ Anvil failed to start${NC}"
        exit 1
    fi
    sleep 1
done
echo ""

# Verify RPC connection
echo "Verifying RPC connection..."
CHAIN_ID=$(curl -s -X POST http://localhost:8545 \
    -H "Content-Type: application/json" \
    -d '{"jsonrpc":"2.0","method":"eth_chainId","params":[],"id":1}' | \
    grep -o '"result":"[^"]*"' | cut -d'"' -f4)

if [ "$CHAIN_ID" = "0x2105" ]; then
    echo -e "${GREEN}✅ Connected to Base (Chain ID: 8453)${NC}"
else
    echo -e "${RED}❌ Unexpected chain ID: $CHAIN_ID${NC}"
    exit 1
fi
echo ""

# Run the test
echo "=================================================="
echo "Running Attestation Tracker CI Test"
echo "=================================================="
echo ""

# Set Python path for imports
export PYTHONPATH="$PROJECT_ROOT/backend:$PYTHONPATH"

# Make script executable
chmod +x ci/test_attestation_tracker_ci.py

# Run the test
if [ "$VERBOSE" = true ]; then
    ./ci/test_attestation_tracker_ci.py || TEST_RESULT=$?
else
    ./ci/test_attestation_tracker_ci.py || TEST_RESULT=$?
fi

echo ""
echo "=================================================="
echo "Test Results"
echo "=================================================="

if [ -z "$TEST_RESULT" ] || [ "$TEST_RESULT" -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo ""
    echo "Summary:"
    echo "  • AttestationTracker deployed successfully"
    echo "  • EIP-712 signatures generated correctly"
    echo "  • Attestations executed through Safe"
    echo "  • Counter incremented as expected"
    echo "  • EAS integration working properly"
    exit 0
else
    echo -e "${RED}❌ TESTS FAILED!${NC}"
    echo ""
    echo "Exit code: $TEST_RESULT"
    echo "Check the output above for details."
    exit $TEST_RESULT
fi