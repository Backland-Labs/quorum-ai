#!/bin/bash
# Fast forward Anvil chain time for testing
# Usage: ./fast_forward_time.sh [seconds]
# Example: ./fast_forward_time.sh 300  (fast forward 5 minutes)

set -e

# Configuration
RPC_URL="${BASE_LEDGER_RPC:-http://localhost:8545}"
TIME_TO_ADVANCE="${1:-300}"  # Default to 5 minutes (300 seconds)

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_header() { echo -e "${BLUE}$1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_info() { echo -e "${YELLOW}⏩ $1${NC}"; }

# Function to format duration
format_duration() {
    local seconds=$1
    local hours=$((seconds / 3600))
    local minutes=$(((seconds % 3600) / 60))
    local secs=$((seconds % 60))
    
    if [ $hours -gt 0 ]; then
        echo "${hours}h ${minutes}m ${secs}s"
    elif [ $minutes -gt 0 ]; then
        echo "${minutes}m ${secs}s"
    else
        echo "${secs}s"
    fi
}

# Function to format timestamp
format_timestamp() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        date -r "$1" "+%Y-%m-%d %H:%M:%S"
    else
        date -d "@$1" "+%Y-%m-%d %H:%M:%S"
    fi
}

# Function to make RPC call
rpc_call() {
    local method=$1
    local params=$2
    curl -s -X POST -H "Content-Type: application/json" \
        --data "{\"jsonrpc\":\"2.0\",\"method\":\"$method\",\"params\":$params,\"id\":1}" \
        "$RPC_URL" | jq -r '.result'
}

# Function to convert hex to decimal
hex_to_dec() {
    echo $((16#${1#0x}))
}

print_header "⏩ Fast Forward Time on Anvil Fork"
echo

# Get current block timestamp
print_header "Getting current time..."
BLOCK_BEFORE=$(rpc_call "eth_getBlockByNumber" '["latest", false]')
TIMESTAMP_BEFORE_HEX=$(echo "$BLOCK_BEFORE" | jq -r '.timestamp')
TIMESTAMP_BEFORE=$(hex_to_dec "$TIMESTAMP_BEFORE_HEX")
TIME_BEFORE=$(format_timestamp "$TIMESTAMP_BEFORE")

echo "  Before: $TIME_BEFORE (timestamp: $TIMESTAMP_BEFORE)"
echo

# Increase time
DURATION_STR=$(format_duration "$TIME_TO_ADVANCE")
print_info "Advancing time by $DURATION_STR ($TIME_TO_ADVANCE seconds)..."

RESULT=$(rpc_call "evm_increaseTime" "[\"0x$(printf '%x' $TIME_TO_ADVANCE)\"]")
print_success "Time advanced"

# Mine a new block to apply the time change
print_info "Mining new block..."
rpc_call "evm_mine" "[]" > /dev/null
print_success "Block mined"
echo

# Get new block timestamp
print_header "Verifying new time..."
BLOCK_AFTER=$(rpc_call "eth_getBlockByNumber" '["latest", false]')
TIMESTAMP_AFTER_HEX=$(echo "$BLOCK_AFTER" | jq -r '.timestamp')
TIMESTAMP_AFTER=$(hex_to_dec "$TIMESTAMP_AFTER_HEX")
TIME_AFTER=$(format_timestamp "$TIMESTAMP_AFTER")

ACTUAL_ADVANCE=$((TIMESTAMP_AFTER - TIMESTAMP_BEFORE))
ACTUAL_STR=$(format_duration "$ACTUAL_ADVANCE")

echo "  After: $TIME_AFTER (timestamp: $TIMESTAMP_AFTER)"
echo "  Time advanced: $ACTUAL_STR ($ACTUAL_ADVANCE seconds)"
echo

if [ $ACTUAL_ADVANCE -ge $TIME_TO_ADVANCE ]; then
    print_success "Time successfully advanced!"
else
    print_info "Note: Actual advancement ($ACTUAL_ADVANCE) differs from requested ($TIME_TO_ADVANCE)"
fi

