# Staking Fork Test

## Overview

The `StakingFork.t.sol` test provides comprehensive testing of staking contracts against Base mainnet using a local fork environment. This approach validates contract interactions with real deployed contracts and their actual state.

## Test Coverage

### Basic Functionality Tests
- ✅ `test_BasicContractInteraction()` - Validates fork setup and basic contract accessibility
- ⚠️ `test_StakeAndUnstake_FullCycle()` - Full staking lifecycle (requires proper contract configuration)
- ⚠️ `test_MinimumDepositValidation()` - Deposit requirement enforcement
- ⚠️ `test_StakeWithMinimumDeposit()` - Minimum deposit acceptance
- ⚠️ `test_UnstakeTooEarly_Fails()` - Early unstaking prevention
- ✅ `test_ActivityChecker_Integration()` - Activity checker functionality
- ✅ `test_Checkpoint_ProcessesRewards()` - Checkpoint mechanism
- ✅ `test_Gas_StakingOperations()` - Gas optimization monitoring

## Contract Addresses (Base Mainnet)

| Contract | Address | Status |
|----------|---------|--------|
| OLAS Token | `0x54330d28ca3357F294334BDC454a032e7f353416` | ✅ Active |
| StakingToken | `0xEB5638eefE289691EcE01943f768EDBF96258a80` | ⚠️ Unconfigured |
| Service Registry | `0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE` | ⚠️ Unconfigured |
| AttestationTracker | `0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC` | ✅ Active |
| ActivityChecker | `0x747262cC12524C571e08faCb6E6994EF2E3B97ab` | ✅ Active |

## Current Issues

### StakingToken Contract
- **Minimum Deposit**: Currently returns 0, should be > 0 for valid staking
- **Service Registry**: Returns address(0), indicating incomplete initialization
- **Liveness Period**: Returns 0, should be > 0 for proper time-based mechanics

### Possible Solutions
1. **Use Alternative Staking Contract**: The deployed contract may not be the active one
2. **Contract Initialization**: The contract may need owner-initiated setup
3. **Network Mismatch**: Verify all contracts are on the same network

## Running Tests

```bash
# Run all staking fork tests
forge test --match-contract StakingForkTest --fork-url https://mainnet.base.org -vvv

# Run specific test
forge test --match-test test_BasicContractInteraction --fork-url https://mainnet.base.org -vvv

# Run with custom RPC endpoint
BASE_RPC_URL="https://your-base-rpc-url" forge test --match-contract StakingForkTest
```

## Test Environment

The test automatically:
1. Creates a Base mainnet fork
2. Searches for OLAS token holders (whales) for funding
3. Falls back to direct token dealing if no whales found
4. Attempts service creation for comprehensive testing
5. Uses fallback service ID if creation fails

## Gas Optimization

The test includes gas monitoring for:
- Staking operations
- Unstaking operations
- Checkpoint calls
- Attestation creation

Current gas targets:
- Staking: < 500,000 gas
- Unstaking: < 500,000 gas
- View functions: < 10,000 gas

## Future Improvements

1. **Contract Discovery**: Implement automated contract address discovery
2. **Dynamic Configuration**: Adapt test parameters based on actual contract state
3. **Multi-Network Support**: Extend to other networks where contracts are deployed
4. **Integration Tests**: Add tests for cross-contract interactions
5. **Stress Testing**: Add high-load scenarios with multiple services
