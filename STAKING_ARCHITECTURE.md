# Olas Staking Architecture Documentation

## Overview

The Olas (Autonolas) staking system is a sophisticated mechanism for incentivizing autonomous agents to actively participate in decentralized governance. This document details how staking works, where the logic resides, and how different components interact.

> **📊 For detailed data flow and contract interactions, see [STAKING_DATA_FLOW.md](./STAKING_DATA_FLOW.md)**

## Architecture Components

Contract locations: https://github.com/valory-xyz/autonolas-registries/tree/a85d0d802c2127b01bc69194df8ef7921d365231/contracts/staking

### 1. Core Staking Contracts

#### StakingBase.sol
The foundational contract containing all core staking logic:
- **Purpose**: Abstract contract with shared staking functionality
- **Key Responsibilities**:
  - Service state management (Unstaked, Staked, Evicted)
  - Reward calculations and distribution
  - Checkpoint and epoch management
  - Activity verification coordination

#### StakingToken.sol
Handles ERC20 token staking:
- Inherits from StakingBase
- Manages OLAS token deposits/withdrawals
- Overrides token-specific transfer methods

#### StakingNativeToken.sol
Handles native token (ETH) staking:
- Inherits from StakingBase
- Manages ETH deposits/withdrawals
- Uses `msg.value` for native token handling

#### StakingFactory.sol
Deployment and management contract:
- Creates new staking instances using CREATE2
- Implements proxy pattern for gas efficiency
- Validates configurations through StakingVerifier

### 2. Activity Validation Layer

#### StakingActivityChecker.sol
Base activity checking interface:
- Abstract contract defining activity validation methods
- Stores `livenessRatio` threshold
- Provides interface for `getMultisigNonces()` and `isRatioPass()`

#### QuorumStakingTokenActivityChecker.sol
Specialized checker for governance voting:
- **Location**: `autonolas-staking-programmes/contracts/externals/backland/`
- **Validates**: Agent participation in DAO voting
- **Metrics Tracked**:
  - Votes cast
  - Voting opportunities considered
  - No-opportunity instances
  - Multisig transaction count

### 3. Data Tracking Contracts

#### QuorumTracker/AttestationTracker (Combined)
Single contract serving dual purpose:
- **As AttestationTracker**: Records and counts attestations
- **As QuorumTracker**: Provides voting statistics interface
- **Address**: `0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC`
- Provides `getVotingStats(multisig)` interface for activity checking

#### AttestationTracker Implementation
Project-specific attestation recording:
- **Location**: `/contracts/src/AttestationTracker.sol`
- **Deployed Address**: `0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC`
- Wraps EAS (Ethereum Attestation Service)
- Tracks agent attestations on-chain
- Optimized storage using bit manipulation
- Also serves as QuorumTracker for the ActivityChecker

## Staking Lifecycle

### 1. Staking Process

```
User initiates stake
        ↓
stake(serviceId) called on StakingToken/StakingNativeToken
        ↓
Routes to StakingBase._stake()
        ↓
Validates:
- Service is registered
- Meets minimum deposit
- Not already staked
        ↓
Transfers tokens from user
        ↓
Records ServiceInfo:
- multisig address
- owner
- agentIds
- timestamp (tsStart)
        ↓
Service enters "Staked" state
```

### 2. Activity Tracking

```
Agent performs actions (voting, attestations)
        ↓
Actions recorded in:
- QuorumTracker (for voting)
- AttestationTracker (for attestations)
        ↓
Periodic checkpoint() called (permissionless)
        ↓
StakingBase.checkpoint() executes
        ↓
Calls ActivityChecker.isRatioPass()
        ↓
Calculates activity ratio:
ratio = (current_actions - last_actions) / time_elapsed
        ↓
Compares against livenessRatio threshold
        ↓
Pass → Accumulate rewards
Fail → Mark as inactive (potential eviction)
```

### 3. Unstaking Process

```
User initiates unstake
        ↓
unstake(serviceId) called
        ↓
Routes to StakingBase._unstake()
        ↓
Calculates final rewards:
- Time-based rewards
- Activity multiplier
- Emission schedule
        ↓
Returns stake + accumulated rewards
        ↓
Service enters "Unstaked" state
        ↓
Tokens transferred to user
```

## Data Structures

### Primary Storage

```solidity
mapping(uint256 => ServiceInfo) public mapServiceInfo;

struct ServiceInfo {
    uint256 multisig;          // Safe multisig address
    address owner;             // Service owner address
    uint256[] agentIds;        // Array of agent IDs
    uint256[] multisigNonces;  // Activity tracking nonces
    uint256 reward;            // Accumulated reward amount
    uint256 tsStart;           // Staking start timestamp
    uint256 tsNext;            // Next checkpoint timestamp
    ServiceState state;        // Current state (Unstaked/Staked/Evicted)
}
```

### Activity Metrics

```solidity
// From QuorumStakingTokenActivityChecker
nonces[0] = multisig.nonce()      // Transaction count
nonces[1] = votingStats[0]        // Votes cast
nonces[2] = votingStats[1]        // Voting opportunities
nonces[3] = votingStats[2]        // No-opportunity count
```

## Key Functions

### Staking Entry Points

| Function | Contract | Description |
|----------|----------|-------------|
| `stake(serviceId)` | StakingToken/NativeToken | Stake a service |
| `unstake(serviceId)` | StakingToken/NativeToken | Unstake and claim rewards |
| `checkpoint()` | StakingBase | Update rewards and check activity |
| `claim(serviceId)` | StakingBase | Claim accumulated rewards |

### Data Access Methods

| Function | Returns | Description |
|----------|---------|-------------|
| `getServiceInfo(serviceId)` | ServiceInfo | Complete staking data |
| `calculateServiceStakingReward(serviceId)` | uint256 | Current reward amount |
| `isServiceStaked(serviceId)` | bool | Staking status |
| `getNextRewardCheckpointTimestamp()` | uint256 | Next checkpoint time |
| `isRatioPass(curNonces, lastNonces, ts)` | bool | Activity validation |

## Reward Calculation

### Base Formula

```
reward = (stakingDeposit * APY * timeStaked) / (365 days * 100)
```

### Activity Multiplier

```
if (activityCheck.isRatioPass()) {
    reward = baseReward * emissionMultiplier
} else {
    reward = 0  // No rewards for inactive services
}
```

### Distribution Methods

1. **Proportional**: Split among all agents based on stake
2. **Owner Only**: All rewards to service owner
3. **Multisig**: Rewards sent to Safe multisig
4. **Custom**: Via configurable reward mechanism

## Integration with Quorum AI

### Backend Services

**ActivityService** (`backend/services/activity_service.py`):
- Monitors daily activity requirements
- Triggers checkpoint updates
- Tracks compliance status

**HealthStatusService** (`backend/services/health_status_service.py`):
- Monitors staking health
- Alerts on activity failures
- Manages eviction prevention

### Configuration

Environment variables connect to staking system:
```bash
ATTESTATION_TRACKER_ADDRESS=0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC
QUORUM_STAKING_ADDRESS=0x747262cC12524C571e08faCb6E6994EF2E3B97ab
EAS_CONTRACT_ADDRESS=0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6
STAKING_FACTORY_ADDRESS=0x1cEe30D08943EB58EFF84DD1AB44a6ee6FEff63a
LIVENESS_RATIO=11574074074074  # ~1 action per day
```

### Smart Contract Integration

1. **AttestationTracker**: Records agent attestations
2. **QuorumStakingTokenActivityChecker**: Validates voting participation
3. **Backend API**: Queries on-chain data and manages agent lifecycle

## Security Considerations

### Access Control
- Only service owners can stake/unstake their services
- Checkpoints are permissionless (anyone can call)
- Activity checkers are immutable once deployed

### Economic Security
- Minimum staking periods prevent gaming
- Activity requirements ensure genuine participation
- Eviction mechanism removes inactive agents

### Storage Optimization
- Bit packing in AttestationTracker reduces gas costs
- Proxy pattern minimizes deployment costs
- Efficient nonce tracking for activity validation

## Contract Addresses (Base Mainnet Deployments)

### Verified and Active Contracts

| Contract | Address | Status | Purpose |
|----------|---------|--------|---------|
| StakingFactory | 0x1cEe30D08943EB58EFF84DD1AB44a6ee6FEff63a | ✅ Deployed | Creates StakingToken instances |
| StakingVerifier | 0x10c5525f77F13b28f42c5626240c001c2d57CaD4 | ✅ Deployed | Validates staking parameters |
| QuorumStakingTokenActivityChecker | 0x747262cC12524C571e08faCb6E6994EF2E3B97ab | ✅ Deployed | Validates agent activity |
| AttestationTracker/QuorumTracker | 0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC | ✅ Deployed | Tracks attestations & voting |
| EAS (Ethereum Attestation Service) | 0xF095fE4b23958b08D38e52d5d5674bBF0C03cbF6 | ✅ Deployed | On-chain attestation service |
| StakingToken | 0xEB5638eefE289691EcE01943f768EDBF96258a80 | ✅ Deployed | Active instance using QuorumActivityChecker |

### Supporting Contracts

| Contract | Address | Purpose |
|----------|---------|---------|
| OLAS Token | 0x54330d28ca3357F294334BDC454a032e7f353416 | Staking token |
| Service Registry | 0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE | Agent/service registration |
| Service Manager Token | 0x63e66d7ad413C01A7b49C7FF4e3Bb765C4E4bd1b | Service management |
| Gnosis Safe Factory | 0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2 | Creates multisig wallets |

### Staking Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Min Staking Deposit** | 10 OLAS | Minimum tokens required to stake |
| **Rewards Per Second** | 824652777778 wei | ~2.13 OLAS/month per service |
| **Max Services** | 2 | Maximum services that can stake |
| **Liveness Period** | 86400 seconds | 24 hour activity check window |
| **Time for Emissions** | 2592000 seconds | 30 day emission period |
| **Min Staking Periods** | 3 | Minimum 3 periods before unstaking |
| **Max Inactivity Periods** | 2 | Evicted after 2 inactive periods |
| **Liveness Ratio** | 11574074074074 | ~1 action per day required |

### Configuration Details
- **Schema UID**: `0x7d917fcbc9a29a9705ff9936ffa599500e4fd902e4486bae317414fe967b307c`
- **Chain ID**: `8453` (Base Mainnet)
- **Activity Checker**: Configured to use QuorumStakingTokenActivityChecker

## Development and Testing

### Local StakingToken Deployment

For comprehensive staking system testing, deploy a properly initialized StakingToken locally using Base mainnet fork:

#### 1. Start Base Mainnet Fork
```bash
# Start Anvil with Base mainnet fork
cd contracts
anvil --fork-url https://mainnet.base.org --fork-block-number 22000000 --host 0.0.0.0 --port 8545
```

#### 2. Deploy Initialized StakingToken
```bash
# Deploy our StakingToken implementation with proper initialization
PRIVATE_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80" \
forge script script/DeployOurStakingToken.s.sol --rpc-url http://localhost:8545 --broadcast -vvv
```

**Deployed Address**: `0x987e855776C03A4682639eEb14e65b3089EE6310`

#### 3. Verify Deployment
```bash
# Verify configuration
cast call 0x987e855776C03A4682639eEb14e65b3089EE6310 "serviceRegistry()(address)" --rpc-url http://localhost:8545
cast call 0x987e855776C03A4682639eEb14e65b3089EE6310 "activityChecker()(address)" --rpc-url http://localhost:8545
cast call 0x987e855776C03A4682639eEb14e65b3089EE6310 "stakingToken()(address)" --rpc-url http://localhost:8545

# Check parameters
cast call 0x987e855776C03A4682639eEb14e65b3089EE6310 "minStakingDeposit()(uint256)" --rpc-url http://localhost:8545
cast call 0x987e855776C03A4682639eEb14e65b3089EE6310 "maxNumServices()(uint256)" --rpc-url http://localhost:8545
cast call 0x987e855776C03A4682639eEb14e65b3089EE6310 "rewardsPerSecond()(uint256)" --rpc-url http://localhost:8545
```

**Expected Results**:
- Service Registry: `0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE`
- Activity Checker: `0x747262cC12524C571e08faCb6E6994EF2E3B97ab`
- OLAS Token: `0x54330d28ca3357F294334BDC454a032e7f353416`
- Min Deposit: `10000000000000000000` (10 OLAS)
- Max Services: `2`
- Rewards Per Second: `824652777778` (~2.13 OLAS/month per service)

#### 4. Run Fork Tests
```bash
# Test the deployed StakingToken with comprehensive fork tests
forge test --match-contract StakingForkTest --fork-url http://localhost:8545 -vvv
```

### Production vs Local Deployment

| Contract | Address | Status | Notes |
|----------|---------|--------|-------|
| **Production StakingToken** | `0xEB5638eefE289691EcE01943f768EDBF96258a80` | ❌ Uninitialized | Returns `address(0)` for configuration |
| **Local StakingToken** | `0x987e855776C03A4682639eEb14e65b3089EE6310` | ✅ Fully Initialized | Ready for comprehensive testing |

### Legacy AttestationTracker Testing
```bash
# Deploy AttestationTracker only
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast

# Run integration tests
uv run pytest tests/integration/test_attestation_tracker_integration.py -v
```

### Verification Commands
```bash
# Check staking status (when StakingToken is deployed)
cast call $STAKING_ADDRESS "isServiceStaked(uint256)" $SERVICE_ID

# Get activity stats from ActivityChecker
cast call 0x747262cC12524C571e08faCb6E6994EF2E3B97ab "getMultisigNonces(address)" $MULTISIG_ADDRESS

# Check attestation count
cast call 0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC "getAttestationCount()(uint256)"

# Get liveness ratio
cast call 0x747262cC12524C571e08faCb6E6994EF2E3B97ab "livenessRatio()(uint256)"

# Check QuorumTracker reference
cast call 0x747262cC12524C571e08faCb6E6994EF2E3B97ab "quorumTracker()(address)"
```

## Summary

The Olas staking architecture implements a sophisticated system for incentivizing autonomous agent participation in governance. Through modular contract design, flexible activity checking, and robust reward mechanisms, it ensures that only actively contributing agents receive staking rewards. The separation of staking logic, activity validation, and data tracking provides a maintainable and extensible system that can adapt to various governance participation requirements.