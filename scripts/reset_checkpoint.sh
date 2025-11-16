#!/bin/bash
# Reset checkpoint time on Anvil fork for testing
# Makes the next checkpoint exactly 24 hours in the future

set -e  # Exit on error

# Configuration
STAKING_CONTRACT="${STAKING_CONTRACT_ADDRESS:-0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb}"
RPC_URL="${BASE_LEDGER_RPC:-http://localhost:8545}"
TS_CHECKPOINT_SLOT=19
LIVENESS_PERIOD=86400  # 24 hours in seconds

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_header() { echo -e "${BLUE}$1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }

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

# Function to convert decimal to hex (padded to 32 bytes)
dec_to_hex() {
    printf "0x%064x" "$1"
}

# Function to format timestamp
format_timestamp() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        date -r "$1" "+%Y-%m-%d %H:%M:%S"
    else
        # Linux
        date -d "@$1" "+%Y-%m-%d %H:%M:%S"
    fi
}

# Function to format duration in hours and minutes
format_duration() {
    local seconds=$1
    local hours=$((seconds / 3600))
    local minutes=$(((seconds % 3600) / 60))
    echo "${hours} hours, ${minutes} minutes"
}

print_header "═══════════════════════════════════════════════════════════"
print_header "  Checkpoint Reset Tool for Anvil Fork"
print_header "═══════════════════════════════════════════════════════════"
echo

# Check if jq is available
if ! command -v jq &> /dev/null; then
    print_error "jq is required but not installed. Please install it:"
    echo "  macOS: brew install jq"
    echo "  Linux: apt-get install jq"
    exit 1
fi

# Check if curl is available
if ! command -v curl &> /dev/null; then
    print_error "curl is required but not installed."
    exit 1
fi

# Test connection
print_header "Connecting to RPC..."
echo "  RPC URL: $RPC_URL"

CHAIN_ID=$(rpc_call "eth_chainId" "[]")
if [ -z "$CHAIN_ID" ]; then
    print_error "Cannot connect to RPC at $RPC_URL"
    exit 1
fi
CHAIN_ID_DEC=$(hex_to_dec "$CHAIN_ID")
print_success "Connected to chain_id=$CHAIN_ID_DEC"
echo

# Get current block timestamp
print_header "Getting current block timestamp..."
BLOCK_HEX=$(rpc_call "eth_getBlockByNumber" '["latest", false]' | jq -r '.timestamp')
CURRENT_TIMESTAMP=$(hex_to_dec "$BLOCK_HEX")
CURRENT_TIME=$(format_timestamp "$CURRENT_TIMESTAMP")
echo "  Current block time: $CURRENT_TIME"
echo "  Current timestamp: $CURRENT_TIMESTAMP"
echo

# Get current tsCheckpoint value
print_header "Reading current tsCheckpoint..."
echo "  Contract: $STAKING_CONTRACT"
echo "  Storage slot: $TS_CHECKPOINT_SLOT"

SLOT_HEX=$(printf "0x%x" "$TS_CHECKPOINT_SLOT")
CURRENT_TS_HEX=$(rpc_call "eth_getStorageAt" "[\"$STAKING_CONTRACT\", \"$SLOT_HEX\", \"latest\"]")
CURRENT_TS=$(hex_to_dec "$CURRENT_TS_HEX")

if [ "$CURRENT_TS" -gt 0 ]; then
    CURRENT_TS_TIME=$(format_timestamp "$CURRENT_TS")
    echo "  Current tsCheckpoint: $CURRENT_TS ($CURRENT_TS_TIME)"
    
    # Calculate how overdue we are
    NEXT_CHECKPOINT=$((CURRENT_TS + LIVENESS_PERIOD))
    NEXT_TIME=$(format_timestamp "$NEXT_CHECKPOINT")
    TIME_DIFF=$((NEXT_CHECKPOINT - CURRENT_TIMESTAMP))
    
    echo "  Next checkpoint was due: $NEXT_TIME"
    
    if [ "$TIME_DIFF" -lt 0 ]; then
        OVERDUE=$((TIME_DIFF * -1))
        OVERDUE_STR=$(format_duration "$OVERDUE")
        print_warning "Checkpoint is OVERDUE by: $OVERDUE_STR"
    else
        REMAINING_STR=$(format_duration "$TIME_DIFF")
        print_success "Checkpoint is NOT overdue. Time remaining: $REMAINING_STR"
    fi
else
    print_warning "No checkpoint has been set yet (tsCheckpoint = 0)"
fi
echo

# Calculate new tsCheckpoint value
print_header "Calculating new checkpoint time..."
# To make next checkpoint 24 hours from now:
# next_checkpoint = tsCheckpoint + livenessPeriod
# We want: next_checkpoint = current_timestamp + 86400
# Since livenessPeriod = 86400, tsCheckpoint = current_timestamp
NEW_TS_CHECKPOINT=$CURRENT_TIMESTAMP
NEW_NEXT_CHECKPOINT=$((NEW_TS_CHECKPOINT + LIVENESS_PERIOD))
NEW_NEXT_TIME=$(format_timestamp "$NEW_NEXT_CHECKPOINT")

echo "  New tsCheckpoint: $NEW_TS_CHECKPOINT ($(format_timestamp "$NEW_TS_CHECKPOINT"))"
echo "  Next checkpoint will be: $NEW_NEXT_CHECKPOINT ($NEW_NEXT_TIME)"
print_success "Time until next checkpoint: 24 hours"
echo

# Set the new value
print_header "Setting new checkpoint time..."
NEW_VALUE_HEX=$(dec_to_hex "$NEW_TS_CHECKPOINT")
SLOT_HEX_PADDED=$(printf "0x%064x" "$TS_CHECKPOINT_SLOT")

echo "  Using anvil_setStorageAt RPC method"
echo "  Contract: $STAKING_CONTRACT"
echo "  Slot: $SLOT_HEX_PADDED"
echo "  Value: $NEW_VALUE_HEX"
echo

RESULT=$(rpc_call "anvil_setStorageAt" "[\"$STAKING_CONTRACT\", \"$SLOT_HEX_PADDED\", \"$NEW_VALUE_HEX\"]")

if [ "$RESULT" = "true" ]; then
    print_success "Storage updated successfully!"
else
    print_error "Failed to update storage. Result: $RESULT"
    exit 1
fi
echo

# Verify the change
print_header "Verifying change..."
VERIFY_HEX=$(rpc_call "eth_getStorageAt" "[\"$STAKING_CONTRACT\", \"$SLOT_HEX\", \"latest\"]")
VERIFY_TS=$(hex_to_dec "$VERIFY_HEX")
VERIFY_TIME=$(format_timestamp "$VERIFY_TS")

echo "  Stored value: $VERIFY_TS ($VERIFY_TIME)"

if [ "$VERIFY_TS" -eq "$NEW_TS_CHECKPOINT" ]; then
    print_success "Verification successful! Checkpoint time is set correctly."
    echo
    print_header "═══════════════════════════════════════════════════════════"
    print_success "Next checkpoint will be at: $NEW_NEXT_TIME"
    print_success "Time until next checkpoint: 24 hours"
    print_header "═══════════════════════════════════════════════════════════"
else
    print_warning "Verification warning: Stored value ($VERIFY_TS) doesn't match target ($NEW_TS_CHECKPOINT)"
fi

