#!/bin/bash

# Quorum AI Local Run Service Script
# This script automates the quickstart process from README.md
# Usage: ./local_run_service.sh [start|stop|logs|status]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Parse command argument
COMMAND=${1:-start}

# Function to print section headers
print_header() {
    echo ""
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${BLUE}  $1${NC}"
    echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Function to stop services
stop_services() {
    print_header "STOPPING QUORUM AI SERVICES"
    
    # Stop Docker container
    if docker ps -q -f name=quorum_app > /dev/null 2>&1; then
        echo "Stopping Docker container..."
        docker stop quorum_app 2>/dev/null || true
        docker rm quorum_app 2>/dev/null || true
        echo -e "${GREEN}[OK] Docker container stopped${NC}"
    else
        echo "No running container found"
    fi
    
    # Stop Anvil
    if [ -f .anvil.pid ]; then
        ANVIL_PID=$(cat .anvil.pid)
        if kill -0 $ANVIL_PID 2>/dev/null; then
            echo "Stopping Anvil (PID: $ANVIL_PID)..."
            kill $ANVIL_PID
            echo -e "${GREEN}[OK] Anvil stopped${NC}"
        fi
        rm .anvil.pid
    else
        echo "No Anvil process found"
    fi
    
    # Clean up log files
    if [ -f anvil.log ]; then
        rm anvil.log
        echo -e "${GREEN}[OK] Cleaned up log files${NC}"
    fi
    
    echo ""
    echo -e "${GREEN}${BOLD}All services stopped${NC}"
    exit 0
}

# Function to show logs
show_logs() {
    print_header "QUORUM AI LOGS"
    
    if ! docker ps -q -f name=quorum_app > /dev/null 2>&1; then
        echo -e "${RED}Container is not running${NC}"
        exit 1
    fi
    
    echo -e "${CYAN}Showing live logs (Ctrl+C to exit)...${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    docker logs -f quorum_app
}

# Function to show status and verify attestations
show_status() {
    print_header "QUORUM AI STATUS & ATTESTATION VERIFICATION"
    
    # Check Anvil status
    if [ -f .anvil.pid ]; then
        ANVIL_PID=$(cat .anvil.pid)
        if kill -0 $ANVIL_PID 2>/dev/null; then
            echo -e "${GREEN}[OK] Anvil is running${NC} (PID: $ANVIL_PID)"
            
            # Get latest block
            BLOCK=$(curl -s -X POST http://localhost:8545 \
                -H "Content-Type: application/json" \
                -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
                2>/dev/null | grep -o '"result":"[^"]*' | cut -d'"' -f4)
            if [ ! -z "$BLOCK" ]; then
                echo "  Latest block: $BLOCK"
            fi
        else
            echo -e "${RED}[FAIL] Anvil is not running${NC}"
        fi
    else
        echo -e "${RED}[FAIL] Anvil is not running${NC}"
    fi
    
    # Check Docker container status
    if docker ps -q -f name=quorum_app > /dev/null 2>&1; then
        echo -e "${GREEN}[OK] Docker container is running${NC}"
        
        # Check health
        HEALTH=$(docker inspect --format='{{.State.Health.Status}}' quorum_app 2>/dev/null || echo "unknown")
        echo "  Health status: $HEALTH"
        
        # Get container stats
        echo "  Resource usage:"
        docker stats --no-stream --format "    CPU: {{.CPUPerc}} | Memory: {{.MemUsage}}" quorum_app
    else
        echo -e "${RED}[FAIL] Docker container is not running${NC}"
    fi
    
    echo ""
    echo -e "${BOLD}Attestation Verification:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Set default values if not already set
    EAS_CONTRACT_ADDRESS="${EAS_CONTRACT_ADDRESS:-0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6}"
    ATTESTATION_TRACKER_ADDRESS="${ATTESTATION_TRACKER_ADDRESS:-0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC}"
    EAS_SCHEMA_UID="${EAS_SCHEMA_UID:-0xc93c2cd5d2027a300cc7ca3d22b36b5581353f6dabab6e14eb41daf76d5b0eb4}"
    
    echo "Contract Addresses:"
    echo "  EAS Contract:        $EAS_CONTRACT_ADDRESS"
    echo "  Attestation Tracker: $ATTESTATION_TRACKER_ADDRESS"
    echo "  Schema UID:          ${EAS_SCHEMA_UID:0:10}..."
    echo ""
    
    # Query attestation count from the contract
    if [ ! -z "$ATTESTATION_TRACKER_ADDRESS" ] && [ -f .anvil.pid ]; then
        echo "Checking attestation count on-chain..."
        
        # Call getAttestationCount() on the contract
        RESULT=$(curl -s -X POST http://localhost:8545 \
            -H "Content-Type: application/json" \
            -d "{
                \"jsonrpc\":\"2.0\",
                \"method\":\"eth_call\",
                \"params\":[{
                    \"to\":\"$ATTESTATION_TRACKER_ADDRESS\",
                    \"data\":\"0x8d8c0063\"
                }, \"latest\"],
                \"id\":1
            }" 2>/dev/null | grep -o '"result":"[^"]*' | cut -d'"' -f4)
        
        if [ ! -z "$RESULT" ] && [ "$RESULT" != "0x" ]; then
            # Convert hex to decimal
            COUNT=$((16#${RESULT:2}))
            echo -e "  ${GREEN}[OK] Total attestations recorded: $COUNT${NC}"
        else
            echo "  No attestations recorded yet"
        fi
    fi
    
    # Check recent Docker logs for attestation activity
    if docker ps -q -f name=quorum_app > /dev/null 2>&1; then
        echo ""
        echo "Recent attestation activity from logs:"
        docker logs quorum_app 2>&1 | tail -n 100 | grep -i "attestation\|attest\|vote" | tail -n 5 || echo "  No recent attestation activity"
    fi
    
    echo ""
    echo -e "${BOLD}Access Points:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    PORT="${PORT:-8716}"
    echo "  Web UI:        http://localhost:${PORT}"
    echo "  Health Check:  http://localhost:${PORT}/healthcheck"
    echo "  API Docs:      http://localhost:${PORT}/docs"
    echo "  RPC Endpoint:  http://localhost:8545"
    
    exit 0
}

# Handle commands
case "$COMMAND" in
    stop)
        stop_services
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    start)
        # Continue with start process
        ;;
    *)
        echo "Usage: $0 [start|stop|logs|status]"
        echo "  start  - Start all services (default)"
        echo "  stop   - Stop all services"
        echo "  logs   - Show live container logs"
        echo "  status - Show service status and attestation verification"
        exit 1
        ;;
esac

print_header "STARTING QUORUM AI LOCAL TESTING"

# Function to check if command exists
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}ERROR: $1 is not installed. Please install it first.${NC}"
        exit 1
    fi
}

# Function to check if port is in use
check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}WARNING: Port $1 is already in use${NC}"
        return 1
    fi
    return 0
}

# Step 1: Check prerequisites
echo -e "${BOLD}Step 1: Checking prerequisites...${NC}"
check_command docker
check_command node
check_command npm
check_command anvil
check_command curl
echo -e "${GREEN}[OK] All prerequisites installed${NC}"
echo ""

# Step 2: Check if ports are available
echo -e "${BOLD}Step 2: Checking port availability...${NC}"
if ! check_port 8545; then
    echo -e "${RED}Port 8545 is in use. Please stop any running Anvil instances.${NC}"
    echo "Run: ./local_run_service.sh stop"
    exit 1
fi
if ! check_port 8716; then
    echo -e "${RED}Port 8716 is in use. Please stop any running Quorum services.${NC}"
    echo "Run: ./local_run_service.sh stop"
    exit 1
fi
echo -e "${GREEN}[OK] Ports 8545 and 8716 are available${NC}"
echo ""

# Step 3: Start Anvil fork of Base mainnet
echo -e "${BOLD}Step 3: Starting local Base mainnet fork with Anvil...${NC}"
echo "This will fork Base mainnet with all deployed contracts"
echo ""

# Start Anvil in background
anvil --fork-url https://mainnet.base.org --host 0.0.0.0 --port 8545 > anvil.log 2>&1 &
ANVIL_PID=$!
echo "Anvil started with PID: $ANVIL_PID"

# Wait for Anvil to be ready
echo "Waiting for Anvil to be ready..."
MAX_ATTEMPTS=10
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s -X POST http://localhost:8545 \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' > /dev/null 2>&1; then
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo -e "${RED}ERROR: Failed to start Anvil. Check anvil.log for details.${NC}"
        exit 1
    fi
    sleep 1
done

# Check if Anvil is running
if ! kill -0 $ANVIL_PID 2>/dev/null; then
    echo -e "${RED}ERROR: Anvil crashed. Check anvil.log for details.${NC}"
    exit 1
fi
echo -e "${GREEN}[OK] Anvil is running and ready${NC}"
echo ""

# Step 3.5: Set default environment variables from README
echo -e "${BOLD}Step 3.5: Setting default environment variables...${NC}"

# Core defaults from README
DEFAULT_MONITORED_DAOS="quorum-ai.eth"

#THIS NEEDS TO BE SET.
DEFAULT_OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-your_openrouter_api_key_here}"

# Contract Addresses (from Base mainnet - as specified in README)
DEFAULT_EAS_CONTRACT_ADDRESS="0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6"
DEFAULT_ATTESTATION_TRACKER_ADDRESS="0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC"
DEFAULT_EAS_SCHEMA_UID="0xc93c2cd5d2027a300cc7ca3d22b36b5581353f6dabab6e14eb41daf76d5b0eb4"

# Network Configuration defaults
DEFAULT_RPC_URL="http://host.docker.internal:8545"
DEFAULT_BASE_RPC_URL="http://host.docker.internal:8545"
DEFAULT_CHAIN_ID="8453"

# Test Account (Anvil default account)
DEFAULT_PRIVATE_KEY="ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
DEFAULT_AGENT_ADDRESS="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

# Safe Configuration defaults. THIS NEEDS TO BE SET.
DEFAULT_SAFE_CONTRACT_ADDRESSES='{"base":"0x"}'

# Server Configuration defaults
DEFAULT_HOST="0.0.0.0"
DEFAULT_PORT="8716"
DEFAULT_DEBUG="true"
DEFAULT_LOG_LEVEL="DEBUG"

# Snapshot Configuration defaults
DEFAULT_SNAPSHOT_GRAPHQL_ENDPOINT="https://testnet.hub.snapshot.org/graphql"
DEFAULT_SNAPSHOT_HUB_URL="https://testnet.seq.snapshot.org/"
DEFAULT_DRY_RUN_DEFAULT="false"

# Use environment variables if set, otherwise use defaults
MONITORED_DAOS="${MONITORED_DAOS:-$DEFAULT_MONITORED_DAOS}"
OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-$DEFAULT_OPENROUTER_API_KEY}"
EAS_CONTRACT_ADDRESS="${EAS_CONTRACT_ADDRESS:-$DEFAULT_EAS_CONTRACT_ADDRESS}"
ATTESTATION_TRACKER_ADDRESS="${ATTESTATION_TRACKER_ADDRESS:-$DEFAULT_ATTESTATION_TRACKER_ADDRESS}"
EAS_SCHEMA_UID="${EAS_SCHEMA_UID:-$DEFAULT_EAS_SCHEMA_UID}"
RPC_URL="${RPC_URL:-$DEFAULT_RPC_URL}"
BASE_RPC_URL="${BASE_RPC_URL:-$DEFAULT_BASE_RPC_URL}"
CHAIN_ID="${CHAIN_ID:-$DEFAULT_CHAIN_ID}"
PRIVATE_KEY="${PRIVATE_KEY:-$DEFAULT_PRIVATE_KEY}"
AGENT_ADDRESS="${AGENT_ADDRESS:-$DEFAULT_AGENT_ADDRESS}"
SAFE_CONTRACT_ADDRESSES="${SAFE_CONTRACT_ADDRESSES:-$DEFAULT_SAFE_CONTRACT_ADDRESSES}"
HOST="${HOST:-$DEFAULT_HOST}"
PORT="${PORT:-$DEFAULT_PORT}"
DEBUG="${DEBUG:-$DEFAULT_DEBUG}"
LOG_LEVEL="${LOG_LEVEL:-$DEFAULT_LOG_LEVEL}"
SNAPSHOT_GRAPHQL_ENDPOINT="${SNAPSHOT_GRAPHQL_ENDPOINT:-$DEFAULT_SNAPSHOT_GRAPHQL_ENDPOINT}"
SNAPSHOT_HUB_URL="${SNAPSHOT_HUB_URL:-$DEFAULT_SNAPSHOT_HUB_URL}"
DRY_RUN_DEFAULT="${DRY_RUN_DEFAULT:-$DEFAULT_DRY_RUN_DEFAULT}"

echo -e "${GREEN}[OK] Environment variables configured${NC}"
echo ""

# Step 3.6: Verify Attestation Tracker deployment on local fork
echo -e "${BOLD}Step 3.6: Verifying Attestation Tracker contract on local fork...${NC}"

TRACKER_ADDRESS="$ATTESTATION_TRACKER_ADDRESS"
echo "Using Attestation Tracker address: $TRACKER_ADDRESS"

# Verify the contract exists by checking its code
echo "Checking if Attestation Tracker contract exists at $TRACKER_ADDRESS..."
CONTRACT_CODE=$(curl -s -X POST http://localhost:8545 \
    -H "Content-Type: application/json" \
    -d "{
        \"jsonrpc\":\"2.0\",
        \"method\":\"eth_getCode\",
        \"params\":[\"$TRACKER_ADDRESS\", \"latest\"],
        \"id\":1
    }" 2>/dev/null | grep -o '"result":"[^"]*' | cut -d'"' -f4)

if [ -z "$CONTRACT_CODE" ] || [ "$CONTRACT_CODE" = "0x" ] || [ "$CONTRACT_CODE" = "null" ]; then
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}${BOLD}ERROR: Attestation Tracker Contract Not Found${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${RED}The Attestation Tracker contract is not deployed at address:${NC}"
    echo -e "${RED}  $TRACKER_ADDRESS${NC}"
    echo ""
    echo -e "${YELLOW}This could mean:${NC}"
    echo -e "${YELLOW}  1. The contract hasn't been deployed to Base mainnet yet${NC}"
    echo -e "${YELLOW}  2. The contract address in your configuration is incorrect${NC}"
    echo -e "${YELLOW}  3. The Base mainnet fork failed to sync properly${NC}"
    echo ""
    echo -e "${CYAN}${BOLD}To fix this issue:${NC}"
    echo -e "${CYAN}  1. Deploy the contract to Base mainnet first, OR${NC}"
    echo -e "${CYAN}  2. Update ATTESTATION_TRACKER_ADDRESS in .env with the correct address${NC}"
    echo -e "${CYAN}  3. For local testing, you may need to deploy contracts locally:${NC}"
    echo -e "${CYAN}     cd contracts && forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast${NC}"
    echo ""
    echo -e "${RED}Stopping Anvil and exiting...${NC}"
    kill $ANVIL_PID 2>/dev/null
    rm -f .anvil.pid
    exit 1
fi

# Verify it's actually our contract by calling a known function
echo "Verifying contract interface..."
# Try to call getAttestationCount() - function selector: 0x8d8c0063
ATTESTATION_COUNT=$(curl -s -X POST http://localhost:8545 \
    -H "Content-Type: application/json" \
    -d "{
        \"jsonrpc\":\"2.0\",
        \"method\":\"eth_call\",
        \"params\":[{
            \"to\":\"$TRACKER_ADDRESS\",
            \"data\":\"0x8d8c0063\"
        }, \"latest\"],
        \"id\":1
    }" 2>/dev/null | grep -o '"result":"[^"]*' | cut -d'"' -f4)

if [ -z "$ATTESTATION_COUNT" ] || [[ "$ATTESTATION_COUNT" == *"error"* ]]; then
    echo -e "${YELLOW}WARNING: Contract exists but couldn't verify interface${NC}"
    echo -e "${YELLOW}The contract at $TRACKER_ADDRESS may not be the Attestation Tracker${NC}"
    echo -e "${YELLOW}Proceeding with caution...${NC}"
else
    # Convert hex to decimal if we got a valid response
    if [ "$ATTESTATION_COUNT" != "0x" ] && [ ! -z "$ATTESTATION_COUNT" ]; then
        COUNT=$((16#${ATTESTATION_COUNT:2}))
        echo -e "${GREEN}[OK] Attestation Tracker verified - Current attestation count: $COUNT${NC}"
    else
        echo -e "${GREEN}[OK] Attestation Tracker verified - No attestations recorded yet${NC}"
    fi
fi

echo -e "${GREEN}[OK] Contract verification complete${NC}"
echo ""

# Step 3.7: Verify EAS contract and Schema
echo -e "${BOLD}Step 3.7: Verifying EAS contract and Schema...${NC}"

EAS_ADDRESS="$EAS_CONTRACT_ADDRESS"
SCHEMA_UID="$EAS_SCHEMA_UID"
echo "Using EAS contract address: $EAS_ADDRESS"
echo "Using EAS Schema UID: $SCHEMA_UID"

# Verify the EAS contract exists
echo "Checking if EAS contract exists at $EAS_ADDRESS..."
EAS_CONTRACT_CODE=$(curl -s -X POST http://localhost:8545 \
    -H "Content-Type: application/json" \
    -d "{
        \"jsonrpc\":\"2.0\",
        \"method\":\"eth_getCode\",
        \"params\":[\"$EAS_ADDRESS\", \"latest\"],
        \"id\":1
    }" 2>/dev/null | grep -o '"result":"[^"]*' | cut -d'"' -f4)

if [ -z "$EAS_CONTRACT_CODE" ] || [ "$EAS_CONTRACT_CODE" = "0x" ] || [ "$EAS_CONTRACT_CODE" = "null" ]; then
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}${BOLD}ERROR: EAS Contract Not Found${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${RED}The Ethereum Attestation Service (EAS) contract is not deployed at:${NC}"
    echo -e "${RED}  $EAS_ADDRESS${NC}"
    echo ""
    echo -e "${YELLOW}This could mean:${NC}"
    echo -e "${YELLOW}  1. The EAS contract address is incorrect${NC}"
    echo -e "${YELLOW}  2. EAS is not deployed on Base mainnet at this address${NC}"
    echo -e "${YELLOW}  3. The Base mainnet fork failed to sync properly${NC}"
    echo ""
    echo -e "${CYAN}${BOLD}To fix this issue:${NC}"
    echo -e "${CYAN}  1. Verify the correct EAS contract address for Base mainnet${NC}"
    echo -e "${CYAN}  2. Update EAS_CONTRACT_ADDRESS in .env with the correct address${NC}"
    echo -e "${CYAN}  3. Check https://docs.attest.org for Base deployment addresses${NC}"
    echo ""
    echo -e "${RED}Stopping Anvil and exiting...${NC}"
    kill $ANVIL_PID 2>/dev/null
    rm -f .anvil.pid
    exit 1
fi

echo -e "${GREEN}[OK] EAS contract found${NC}"

# Verify the schema exists in EAS
echo "Verifying EAS Schema registration..."
# Call getSchema(bytes32) - function selector: 0xa2ea7c6e
# Remove 0x prefix from schema UID if present
SCHEMA_UID_CLEAN=${SCHEMA_UID#0x}
# Pad the schema UID to 32 bytes (64 hex characters)
PADDED_SCHEMA=$(printf "0xa2ea7c6e%064s" "$SCHEMA_UID_CLEAN")

SCHEMA_RESULT=$(curl -s -X POST http://localhost:8545 \
    -H "Content-Type: application/json" \
    -d "{
        \"jsonrpc\":\"2.0\",
        \"method\":\"eth_call\",
        \"params\":[{
            \"to\":\"$EAS_ADDRESS\",
            \"data\":\"$PADDED_SCHEMA\"
        }, \"latest\"],
        \"id\":1
    }" 2>/dev/null)

# Check if we got an error or empty result
if [[ "$SCHEMA_RESULT" == *"error"* ]]; then
    echo -e "${YELLOW}WARNING: Could not verify schema registration${NC}"
    echo -e "${YELLOW}The EAS contract exists but schema verification failed${NC}"
    echo -e "${YELLOW}This might be normal if the schema hasn't been registered yet${NC}"
    echo -e "${YELLOW}Proceeding with setup...${NC}"
else
    # Extract the result
    SCHEMA_DATA=$(echo "$SCHEMA_RESULT" | grep -o '"result":"[^"]*' | cut -d'"' -f4)
    
    # Check if the schema exists (non-zero result indicates registered schema)
    if [ ! -z "$SCHEMA_DATA" ] && [ "$SCHEMA_DATA" != "0x" ] && [ "$SCHEMA_DATA" != "0x0000000000000000000000000000000000000000000000000000000000000000" ]; then
        echo -e "${GREEN}[OK] EAS Schema verified - UID: ${SCHEMA_UID:0:10}...${NC}"
        
        # Try to decode the schema data to show what fields it contains
        # The result contains: uid, resolver, revocable, schema (as a string)
        echo "  Schema is registered and available for attestations"
    else
        echo -e "${YELLOW}WARNING: Schema UID not found in EAS registry${NC}"
        echo -e "${YELLOW}Schema UID: $SCHEMA_UID${NC}"
        echo -e "${YELLOW}You may need to register this schema before creating attestations${NC}"
        echo ""
        echo -e "${CYAN}To register a schema:${NC}"
        echo -e "${CYAN}  1. Use the EAS SDK or web interface${NC}"
        echo -e "${CYAN}  2. Or deploy with: cd contracts && forge script script/RegisterSchema.s.sol --rpc-url http://localhost:8545 --broadcast${NC}"
        echo -e "${YELLOW}Proceeding with setup (attestations may fail)...${NC}"
    fi
fi

echo -e "${GREEN}[OK] EAS verification complete${NC}"
echo ""

# Step 4: Display configuration summary
echo -e "${BOLD}Step 4: Configuration Summary${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Monitored DAOs:          $MONITORED_DAOS"
echo "Attestation Tracker:     ${ATTESTATION_TRACKER_ADDRESS:0:10}..."
echo "EAS Contract:            ${EAS_CONTRACT_ADDRESS:0:10}..."
echo "Schema UID:              ${EAS_SCHEMA_UID:0:10}..."
echo "Chain ID:                $CHAIN_ID"
echo "Agent Address:           $AGENT_ADDRESS"
if [ "$OPENROUTER_API_KEY" = "your_openrouter_api_key_here" ]; then
    echo -e "${YELLOW}OpenRouter API Key:      NOT SET (using default placeholder)${NC}"
    echo -e "${YELLOW}                         Update with: export OPENROUTER_API_KEY='your_actual_key'${NC}"
else
    echo "OpenRouter API Key:      ${OPENROUTER_API_KEY:0:10}..."
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Step 5: Pull or build Docker image
echo -e "${BOLD}Step 5: Preparing Docker image...${NC}"
if docker image inspect backlandlabs/quorum:latest >/dev/null 2>&1; then
    echo "Using existing Docker image"
else
    echo "Pulling Docker image..."
    docker pull backlandlabs/quorum:latest || {
        echo -e "${YELLOW}WARNING: Could not pull image, will try to build locally${NC}"
        if [ -f Dockerfile ]; then
            docker build -t backlandlabs/quorum:latest .
        else
            echo -e "${RED}ERROR: No Dockerfile found and cannot pull image${NC}"
            kill $ANVIL_PID 2>/dev/null
            exit 1
        fi
    }
fi
echo -e "${GREEN}[OK] Docker image ready${NC}"
echo ""

# Step 6: Fund the Safe multisig for attestation transactions
echo -e "${BOLD}Step 6: Funding Safe multisig for attestation transactions...${NC}"

# Extract Safe address from configuration
SAFE_ADDRESS=$(echo "$SAFE_CONTRACT_ADDRESSES" | grep -o '"base":"[^"]*"' | cut -d'"' -f4 2>/dev/null)

if [ -z "$SAFE_ADDRESS" ] || [ "$SAFE_ADDRESS" = "null" ]; then
    echo -e "${YELLOW}WARNING: No Safe address configured, using default Anvil account${NC}"
    SAFE_ADDRESS="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
fi

echo "Using Safe address: $SAFE_ADDRESS"

# Check current balance of the Safe
SAFE_BALANCE=$(curl -s -X POST http://localhost:8545 \
    -H "Content-Type: application/json" \
    -d "{
        \"jsonrpc\":\"2.0\",
        \"method\":\"eth_getBalance\",
        \"params\":[\"$SAFE_ADDRESS\", \"latest\"],
        \"id\":1
    }" 2>/dev/null | grep -o '"result":"[^"]*' | cut -d'"' -f4)

if [ ! -z "$SAFE_BALANCE" ] && [ "$SAFE_BALANCE" != "0x" ]; then
    # Convert hex to decimal and check if balance is sufficient (< 0.1 ETH)
    BALANCE_WEI=$((16#${SAFE_BALANCE:2}))
    BALANCE_ETH=$(echo "scale=6; $BALANCE_WEI / 1000000000000000000" | bc -l 2>/dev/null || echo "0")
    
    echo "Current Safe balance: ${BALANCE_ETH} ETH"
    
    # Check if balance is less than 0.1 ETH (threshold for funding)
    NEEDS_FUNDING=0
    if command -v bc >/dev/null 2>&1; then
        NEEDS_FUNDING=$(echo "$BALANCE_ETH < 0.1" | bc -l)
    else
        # Fallback: check if balance is very small (less than 10^17 wei = 0.1 ETH)
        if [ "$BALANCE_WEI" -lt "100000000000000000" ]; then
            NEEDS_FUNDING=1
        fi
    fi
    
    if [ "$NEEDS_FUNDING" = "1" ]; then
        echo "Safe balance is insufficient for attestation transactions, funding with 1 ETH..."
        
        # Check if cast is available
        if command -v cast >/dev/null 2>&1; then
            # Fund the Safe with 1 ETH using the default Anvil account
            FUNDING_RESULT=$(cast send --private-key "$PRIVATE_KEY" \
                --rpc-url http://localhost:8545 \
                "$SAFE_ADDRESS" \
                --value 1ether 2>&1)
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}[OK] Safe successfully funded with 1 ETH${NC}"
            else
                echo -e "${YELLOW}WARNING: Failed to fund Safe with cast, trying curl method...${NC}"
                
                # Fallback to raw transaction via curl
                FUND_TX=$(curl -s -X POST http://localhost:8545 \
                    -H "Content-Type: application/json" \
                    -d "{
                        \"jsonrpc\":\"2.0\",
                        \"method\":\"eth_sendTransaction\",
                        \"params\":[{
                            \"from\":\"$AGENT_ADDRESS\",
                            \"to\":\"$SAFE_ADDRESS\",
                            \"value\":\"0xde0b6b3a7640000\"
                        }],
                        \"id\":1
                    }" 2>/dev/null)
                
                if [[ "$FUND_TX" == *"error"* ]]; then
                    echo -e "${YELLOW}WARNING: Could not fund Safe automatically${NC}"
                    echo -e "${YELLOW}Attestation transactions may fail due to insufficient funds${NC}"
                    echo -e "${YELLOW}You may need to fund the Safe manually:${NC}"
                    echo -e "${YELLOW}  cast send --private-key $PRIVATE_KEY --rpc-url http://localhost:8545 $SAFE_ADDRESS --value 1ether${NC}"
                else
                    echo -e "${GREEN}[OK] Safe successfully funded with 1 ETH${NC}"
                fi
            fi
        else
            echo -e "${YELLOW}WARNING: 'cast' command not found${NC}"
            echo -e "${YELLOW}Cannot automatically fund Safe for attestation transactions${NC}"
            echo -e "${YELLOW}Install Foundry or fund Safe manually:${NC}"
            echo -e "${YELLOW}  curl -X POST http://localhost:8545 -H \"Content-Type: application/json\" -d '{\"jsonrpc\":\"2.0\",\"method\":\"eth_sendTransaction\",\"params\":[{\"from\":\"$AGENT_ADDRESS\",\"to\":\"$SAFE_ADDRESS\",\"value\":\"0xde0b6b3a7640000\"}],\"id\":1}'${NC}"
        fi
    else
        echo -e "${GREEN}[OK] Safe has sufficient balance for attestation transactions${NC}"
    fi
else
    echo -e "${YELLOW}WARNING: Could not check Safe balance${NC}"
    echo -e "${YELLOW}Proceeding with setup, but attestation transactions may fail${NC}"
fi

echo ""

# Step 7: Start Docker container directly
echo -e "${BOLD}Step 7: Starting Quorum AI service...${NC}"

# Stop any existing container
docker stop quorum_app 2>/dev/null || true
docker rm quorum_app 2>/dev/null || true

# Check if ethereum_private_key.txt exists and prepare volume mount
VOLUME_MOUNT=""
if [ -f "ethereum_private_key.txt" ]; then
    echo "Found ethereum_private_key.txt - will mount into container"
    VOLUME_MOUNT="-v $(pwd)/ethereum_private_key.txt:/app/ethereum_private_key.txt"
elif [ -f "backend/ethereum_private_key.txt" ]; then
    echo "Found backend/ethereum_private_key.txt - will mount into container"
    VOLUME_MOUNT="-v $(pwd)/backend/ethereum_private_key.txt:/app/ethereum_private_key.txt"
else
    echo -e "${YELLOW}ethereum_private_key.txt not found - creating with default test key${NC}"
    # Create the file with the default Anvil test account private key (without 0x prefix)
    echo "${PRIVATE_KEY#0x}" > ethereum_private_key.txt
    echo -e "${GREEN}[OK] Created ethereum_private_key.txt with test private key${NC}"
    VOLUME_MOUNT="-v $(pwd)/ethereum_private_key.txt:/app/ethereum_private_key.txt"
fi

# Run Docker container with all environment variables and optional volume mount
echo "Starting container with environment configuration..."
docker run -d \
    --name quorum_app \
    --add-host=host.docker.internal:host-gateway \
    -p ${PORT}:${PORT} \
    ${VOLUME_MOUNT} \
    -e MONITORED_DAOS="$MONITORED_DAOS" \
    -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
    -e EAS_CONTRACT_ADDRESS="$EAS_CONTRACT_ADDRESS" \
    -e ATTESTATION_TRACKER_ADDRESS="$ATTESTATION_TRACKER_ADDRESS" \
    -e EAS_SCHEMA_UID="$EAS_SCHEMA_UID" \
    -e RPC_URL="$RPC_URL" \
    -e BASE_RPC_URL="$BASE_RPC_URL" \
    -e CHAIN_ID="$CHAIN_ID" \
    -e PRIVATE_KEY="$PRIVATE_KEY" \
    -e AGENT_ADDRESS="$AGENT_ADDRESS" \
    -e SAFE_CONTRACT_ADDRESSES="$SAFE_CONTRACT_ADDRESSES" \
    -e HOST="$HOST" \
    -e PORT="$PORT" \
    -e DEBUG="$DEBUG" \
    -e LOG_LEVEL="$LOG_LEVEL" \
    -e SNAPSHOT_GRAPHQL_ENDPOINT="$SNAPSHOT_GRAPHQL_ENDPOINT" \
    -e SNAPSHOT_HUB_URL="$SNAPSHOT_HUB_URL" \
    -e DRY_RUN_DEFAULT="$DRY_RUN_DEFAULT" \
    -e PUBLIC_API_BASE_URL="http://localhost:${PORT}" \
    backlandlabs/quorum:latest

# Wait for service to be ready
echo "Waiting for service to be ready..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if curl -s -f http://localhost:${PORT}/healthcheck > /dev/null 2>&1; then
        echo -e "${GREEN}[OK] Quorum AI service is running${NC}"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo -e "${RED}ERROR: Service failed to start. Check logs with: docker logs quorum_app${NC}"
        kill $ANVIL_PID 2>/dev/null
        exit 1
    fi
    sleep 2
done
echo ""

# Save Anvil PID for stop command
echo $ANVIL_PID > .anvil.pid

# Step 8: Display success information
print_header "QUORUM AI IS RUNNING SUCCESSFULLY!"

echo -e "${BOLD}${GREEN}For Auditors - Verification Steps:${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "1. ${BOLD}Verify Status:${NC}"
echo "   ./local_run_service.sh status"
echo "   This shows:"
echo "   - Service health status"
echo "   - Attestation count on blockchain"
echo "   - Recent voting activity"
echo ""
echo "2. ${BOLD}Monitor Live Activity:${NC}"
echo "   ./local_run_service.sh logs"
echo "   Watch for:"
echo "   - Proposal fetching"
echo "   - AI analysis decisions"
echo "   - Attestation transactions"
echo ""
echo "3. ${BOLD}Access Points:${NC}"
echo "   - Web UI:        http://localhost:${PORT}"
echo "   - Health Check:  http://localhost:${PORT}/healthcheck"
echo "   - API Docs:      http://localhost:${PORT}/docs"
echo "   - RPC Endpoint:  http://localhost:8545"
echo ""
echo "4. ${BOLD}Stop Services:${NC}"
echo "   ./local_run_service.sh stop"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
if [ "$OPENROUTER_API_KEY" = "your_openrouter_api_key_here" ]; then
    echo -e "${YELLOW}Important: Set your OpenRouter API key before use:${NC}"
    echo -e "${YELLOW}  export OPENROUTER_API_KEY='your_actual_api_key'${NC}"
    echo -e "${YELLOW}  Then restart: ./local_run_service.sh stop && ./local_run_service.sh start${NC}"
    echo ""
fi

# Show initial logs
echo -e "${BOLD}Initial service logs (last 20 lines):${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
docker logs --tail 20 quorum_app 2>&1