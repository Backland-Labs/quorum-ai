# QuorumTracker Smart Contract

This directory contains the QuorumTracker smart contract implementation for tracking multisig voting activity. The contract is designed to work with Autonolas QuorumStakingTokenActivityChecker.

## Overview

The QuorumTracker contract maintains simple counters for three activity types:
- **VOTES_CAST (0)**: Number of votes cast by the multisig
- **OPPORTUNITIES_CONSIDERED (1)**: Number of proposal opportunities considered
- **NO_OPPORTUNITIES (2)**: Number of periods with no voting opportunities

## Project Structure

```
contracts/
├── src/
│   └── QuorumTracker.sol       # Main contract implementation
├── test/
│   └── QuorumTracker.t.sol     # Comprehensive test suite
├── script/
│   └── Deploy.s.sol            # Deployment script
├── lib/                        # Dependencies (forge-std, OpenZeppelin)
├── foundry.toml                # Foundry configuration
└── remappings.txt              # Import remappings
```

## Quick Start

### Prerequisites
- [Foundry](https://book.getfoundry.sh/getting-started/installation) installed
- Git submodules initialized

### Installation

```bash
cd contracts

# Install dependencies (if not already present)
forge install

# Build contracts
forge build

# Run tests
forge test -vvv

# Generate gas report
forge test --gas-report
```

### Deployment

Deploy to local testnet:

```bash
# Start Anvil (in separate terminal)
anvil --fork-url $BASE_RPC_URL --chain-id 31337

# Set environment variables
export PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
export QUORUM_TRACKER_OWNER=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# Deploy contract
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast
```

## Contract Interface

### Functions

#### `register(address multisig, uint8 activityType)`
- **Access**: Owner only
- **Purpose**: Increments the activity counter for a multisig address
- **Parameters**:
  - `multisig`: The multisig address to track
  - `activityType`: 0, 1, or 2 (see constants above)

#### `getVotingStats(address multisig) returns (uint256[] memory)`
- **Access**: Public view
- **Purpose**: Returns the activity statistics for a multisig
- **Returns**: 3-element array `[votes_cast, opportunities_considered, no_opportunities]`

### Constants

- `VOTES_CAST = 0`
- `OPPORTUNITIES_CONSIDERED = 1`
- `NO_OPPORTUNITIES = 2`

## Testing

The contract includes comprehensive tests covering:

- ✅ Access control (owner-only registration)
- ✅ Activity registration for all types
- ✅ Statistics retrieval and validation
- ✅ Invalid activity type rejection
- ✅ Multiple registrations and multisigs
- ✅ Fuzz testing for edge cases
- ✅ Gas optimization verification

### Run Tests

```bash
# Run all tests with verbose output
forge test -vvv

# Run specific test contract
forge test --match-contract QuorumTrackerTest

# Run tests with gas reporting
forge test --gas-report

# Check test coverage
forge coverage
```

## Integration

This contract is designed to integrate with the quorum-ai backend service:

1. **Backend Configuration**: Set `QUORUM_TRACKER_ADDRESS` and `QUORUM_TRACKER_OWNER` environment variables
2. **Service Integration**: The `QuorumTrackerService` handles contract interactions
3. **Agent Workflow**: Activities are automatically registered during agent runs
4. **Statistics Query**: Autonolas can query voting statistics via `getVotingStats()`

## Security Considerations

- ✅ **Access Control**: Only owner can register activities
- ✅ **Input Validation**: Activity type must be ≤ 2
- ✅ **Gas Efficiency**: Simple counter increments minimize gas costs
- ✅ **State Consistency**: Independent tracking per multisig address
- ✅ **No External Calls**: Self-contained contract with no external dependencies

## Gas Usage

Approximate gas costs (subject to network conditions):
- **Deployment**: ~400,000 gas
- **Register Activity**: ~50,000 gas
- **Get Statistics**: ~10,000 gas (view function)

## ABI Compatibility

The contract ABI is compatible with `backend/abi/quorum_tracker.json` and includes:
- Constructor with `initialOwner` parameter
- Owner-only `register` function
- Public `getVotingStats` function
- Public constant getters and stats mapping access

## License

MIT License - see LICENSE file for details.
