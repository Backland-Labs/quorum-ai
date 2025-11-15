#!/usr/bin/env bash
#
# Fund the Safe contract with ETH for testing
# This script transfers ETH from the Anvil default test account to the Safe contract

set -euo pipefail

# Configuration
SAFE_ADDRESS="${SAFE_ADDRESS:-0x07edA994E013AbC8619A5038455db3A6FBdd2Bca}"
RPC_URL="${RPC_URL:-http://localhost:8545}"
TEST_PRIVATE_KEY="${TEST_PRIVATE_KEY:-0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80}"
TEST_ADDRESS="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
FUNDING_AMOUNT="${FUNDING_AMOUNT:-1ether}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[FUND]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[FUND]${NC} $1"
}

log_error() {
    echo -e "${RED}[FUND]${NC} $1"
}

# Check if cast is available
if ! command -v cast &> /dev/null; then
    log_error "cast command not found. Please install Foundry (https://book.getfoundry.sh/getting-started/installation)"
    exit 1
fi

# Check if RPC is available - try both localhost and wait for it to be ready
MAX_RETRIES=30
RETRY_COUNT=0
RPC_READY=false

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if cast block-number --rpc-url "$RPC_URL" &> /dev/null; then
        RPC_READY=true
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        log_info "Waiting for RPC to be ready... (attempt $RETRY_COUNT/$MAX_RETRIES)"
        sleep 2
    fi
done

if [ "$RPC_READY" = false ]; then
    log_error "Cannot connect to RPC at $RPC_URL after $MAX_RETRIES attempts. Is Anvil running?"
    exit 1
fi

log_info "RPC is ready at $RPC_URL"

# Get initial balances
log_info "Checking current balances..."
test_balance=$(cast balance "$TEST_ADDRESS" --rpc-url "$RPC_URL" 2>/dev/null || echo "0")
safe_balance_before=$(cast balance "$SAFE_ADDRESS" --rpc-url "$RPC_URL" 2>/dev/null || echo "0")

# Convert wei to ether for display
test_balance_eth=$(cast to-unit "$test_balance" ether 2>/dev/null || echo "0")
safe_balance_before_eth=$(cast to-unit "$safe_balance_before" ether 2>/dev/null || echo "0")

log_info "Test account balance: $test_balance_eth ETH"
log_info "Safe balance (before): $safe_balance_before_eth ETH"

# Check if Safe already has sufficient balance (>= 0.5 ETH)
min_balance_wei=$(cast to-wei 0.5 ether)
if [ "$safe_balance_before" -ge "$min_balance_wei" ]; then
    log_info "Safe already has sufficient balance ($safe_balance_before_eth ETH >= 0.5 ETH). Skipping funding."
    exit 0
fi

# Fund the Safe contract
log_info "Funding Safe contract at $SAFE_ADDRESS with $FUNDING_AMOUNT..."
if cast send \
    --rpc-url "$RPC_URL" \
    --private-key "$TEST_PRIVATE_KEY" \
    --value "$FUNDING_AMOUNT" \
    "$SAFE_ADDRESS" \
    &> /dev/null; then

    # Verify the transfer
    sleep 1
    safe_balance_after=$(cast balance "$SAFE_ADDRESS" --rpc-url "$RPC_URL")
    safe_balance_after_eth=$(cast to-unit "$safe_balance_after" ether)

    if [ "$safe_balance_after" -gt "$safe_balance_before" ]; then
        log_info "✓ Safe funded successfully!"
        log_info "Safe balance (after): $safe_balance_after_eth ETH"
        log_info "Funded amount: $(cast to-unit $((safe_balance_after - safe_balance_before)) ether) ETH"
        exit 0
    else
        log_error "Transfer succeeded but balance didn't increase"
        exit 1
    fi
else
    log_error "Failed to fund Safe contract"
    exit 1
fi
