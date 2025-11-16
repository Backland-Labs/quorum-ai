# Checkpoint Testing Tools for Anvil Fork

Shell scripts to manipulate staking contract checkpoint time and chain time for testing.

## Quick Start

```bash
# Reset checkpoint to 24 hours
./scripts/reset_checkpoint.sh

# Fast forward time by 5 minutes
./scripts/fast_forward_time.sh 300
```

## Problem

The staking contract on the Anvil fork was overdue by 201 hours, making it impossible to test the "Time to Next Checkpoint" functionality. The contract needs to be in a state where the next checkpoint is exactly 24 hours in the future.

## Solution

Two scripts provide complete control over checkpoint timing:
- `reset_checkpoint.sh` - Uses `anvil_setStorageAt` to set the checkpoint to current time (making next checkpoint 24 hours away)
- `fast_forward_time.sh` - Uses `evm_increaseTime` and `evm_mine` to advance the chain time

## Scripts

### 1. reset_checkpoint.sh - Reset Checkpoint to 24 Hours

```bash
./scripts/reset_checkpoint.sh
```

The script will:
1. Connect to your Anvil fork
2. Read the current checkpoint status
3. Calculate the new checkpoint time
4. Update the contract storage
5. Verify the change worked

### 2. fast_forward_time.sh - Fast Forward Chain Time

```bash
# Fast forward 5 minutes (default)
./scripts/fast_forward_time.sh

# Fast forward custom duration
./scripts/fast_forward_time.sh <seconds>
```

Examples:
- 5 minutes: `./scripts/fast_forward_time.sh 300`
- 1 hour: `./scripts/fast_forward_time.sh 3600`
- 12 hours: `./scripts/fast_forward_time.sh 43200`
- 23 hours: `./scripts/fast_forward_time.sh 82800`

### Example Output

```
═══════════════════════════════════════════════════════════
  Checkpoint Reset Tool for Anvil Fork
═══════════════════════════════════════════════════════════

Connecting to RPC...
  RPC URL: http://localhost:8545
✅ Connected to chain_id=8453

Getting current block timestamp...
  Current block time: 2025-11-16 14:07:32
  Current timestamp: 1763330852

Reading current tsCheckpoint...
  Contract: 0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb
  Storage slot: 19
  Current tsCheckpoint: 1763330710 (2025-11-16 14:05:10)
  Next checkpoint was due: 2025-11-17 14:05:10
✅ Checkpoint is NOT overdue. Time remaining: 23 hours, 57 minutes

Calculating new checkpoint time...
  New tsCheckpoint: 1763330852 (2025-11-16 14:07:32)
  Next checkpoint will be: 1763417252 (2025-11-17 14:07:32)
✅ Time until next checkpoint: 24 hours

Setting new checkpoint time...
  Using anvil_setStorageAt RPC method
  Contract: 0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb
  Slot: 0x0000000000000000000000000000000000000000000000000000000000000013
  Value: 0x00000000000000000000000000000000000000000000000000000000691a4b24

✅ Storage updated successfully!

Verifying change...
  Stored value: 1763330852 (2025-11-16 14:07:32)
✅ Verification successful! Checkpoint time is set correctly.

═══════════════════════════════════════════════════════════
✅ Next checkpoint will be at: 2025-11-17 14:07:32
✅ Time until next checkpoint: 24 hours
═══════════════════════════════════════════════════════════
```

## Configuration

The script uses environment variables for configuration:

```bash
# Staking contract address (optional)
export STAKING_CONTRACT_ADDRESS="0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb"

# RPC endpoint (optional)
export BASE_LEDGER_RPC="http://localhost:8545"
```

If not set, the script uses the defaults shown above.

## Requirements

- **Anvil fork** running locally
- **curl** - HTTP client for RPC calls
- **jq** - JSON processor for parsing responses
  - macOS: `brew install jq`
  - Linux: `apt-get install jq`

## Technical Details

### Storage Layout

Based on the `StakingBase.sol` contract:
- **Slot 19**: `tsCheckpoint` (uint256) - Last checkpoint timestamp
- **Slot 5**: `livenessPeriod` (uint256) - Period between checkpoints (86400 seconds = 24 hours)

### Next Checkpoint Calculation

```
next_checkpoint = tsCheckpoint + livenessPeriod
```

To make `next_checkpoint` = `current_time + 24_hours`:
```
tsCheckpoint = current_time + 24_hours - livenessPeriod
tsCheckpoint = current_time  (when livenessPeriod = 24 hours)
```

### What It Does

1. **Connects** to the Anvil fork via RPC
2. **Reads** current block timestamp
3. **Checks** current `tsCheckpoint` value and calculates if overdue
4. **Calculates** new `tsCheckpoint` = current_timestamp
5. **Executes** `anvil_setStorageAt` RPC call to update storage slot 19
6. **Verifies** the change by reading the storage slot again
7. **Reports** success with new checkpoint time

## Results

**Before:**
```
⚠️  Checkpoint is OVERDUE by: 201 hours, 44 minutes
```

**After:**
```
✅ Checkpoint is NOT overdue. Time remaining: 24 hours
✅ Next checkpoint will be at: 2025-11-17 14:07:32
```

## Notes

- ✅ Only works with Anvil/Hardhat forks that support `anvil_setStorageAt`
- ✅ Will not work on live networks (by design)
- ✅ Safe to run multiple times - just resets to current time
- ✅ Colored output for easy reading
- ✅ Automatic verification of changes
- ✅ Works on both macOS and Linux

## Troubleshooting

### "jq: command not found"
Install jq:
```bash
# macOS
brew install jq

# Linux
sudo apt-get install jq
```

### "Cannot connect to RPC"
Make sure your Anvil fork is running:
```bash
# Test connection
curl -X POST -H "Content-Type: application/json" \
  --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  http://localhost:8545
```

### Wrong storage slot
If the contract has been modified, storage slot 19 might be incorrect. You can modify the `TS_CHECKPOINT_SLOT` variable at the top of the script.

## Testing Countdown UI

### Reset to 24 Hours
```bash
./scripts/reset_checkpoint.sh
```

### Fast Forward to Test Different States

**Test countdown in last hour:**
```bash
./scripts/reset_checkpoint.sh
./scripts/fast_forward_time.sh 82800  # Jump to 1 hour before deadline
```

**Test countdown in last 5 minutes:**
```bash
./scripts/reset_checkpoint.sh
./scripts/fast_forward_time.sh 86100  # Jump to 5 minutes before deadline
```

**Test overdue state:**
```bash
./scripts/reset_checkpoint.sh
./scripts/fast_forward_time.sh 86500  # Jump 100 seconds past deadline
```

**Gradual countdown testing:**
```bash
./scripts/reset_checkpoint.sh
./scripts/fast_forward_time.sh 300    # Advance 5 minutes
./scripts/fast_forward_time.sh 300    # Advance another 5 minutes
./scripts/fast_forward_time.sh 3600   # Advance 1 hour
```

## Integration with Testing

Add to your test setup:
```bash
# Start Anvil fork
docker-compose -f docker-compose.fork.yml up -d

# Wait for fork to be ready
sleep 5

# Reset checkpoint for testing
./scripts/reset_checkpoint.sh

# Run your tests
npm run test
```

## Verification

To verify the checkpoint is set correctly, you can also check using the backend script:

```bash
cd backend && uv run python scripts/check_staking_status.py
```

This should show:
```
Status: ✅ NOT OVERDUE
Time until next checkpoint: ~24 hours
```
