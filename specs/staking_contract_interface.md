# Staking Contract Interface

**Contract Address (Proxy):** `0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb`
**Implementation Address:** `0xEB5638eefE289691EcE01943f768EDBF96258a80`
**Network:** Base Mainnet
**Type:** Olas/Autonolas StakingToken Proxy

## Overview

This is a proxy contract that forwards calls to the StakingToken implementation. It's part of the Olas/Autonolas staking system on Base mainnet.

## Proxy Functions

- `getImplementation()` → `address` - Returns the implementation contract address
- Fallback function delegates all other calls to the implementation

## Core Staking Functions

### State-Modifying Functions

- `stake(uint256 serviceId)` - Stake a service
- `unstake(uint256 serviceId)` → `uint256` - Unstake a service (returns reward amount)
- `claim(uint256 serviceId)` → `uint256` - Claim rewards for a staked service
- `checkpointAndClaim(uint256 serviceId)` → `uint256` - Checkpoint then claim in one call
- `checkpoint()` → `(uint256[], uint256[], uint256[], uint256[])` - Update checkpoint (returns arrays: serviceIds, rewards, rewardsPerSecond, nonces)
- `deposit(uint256 amount)` - Deposit staking tokens
- `forcedUnstake(uint256 serviceId)` - Force unstake (admin/emergency)

### View Functions - Service Info

- `getServiceIds()` → `uint256[]` - Get all staked service IDs
- `getAgentIds()` → `uint256[]` - Get all agent IDs
- `getServiceInfo(uint256 serviceId)` → `ServiceInfo` - Get detailed service info
  - Returns: `(address multisig, address owner, uint256 nonces, uint256 tsStart, uint256 reward)`
- `getStakingState(uint256 serviceId)` → `StakingState` - Get staking state for a service

### View Functions - Rewards

- `availableRewards()` → `uint256` - Total available rewards
- `balance()` → `uint256` - Contract balance
- `calculateStakingReward(uint256 serviceId)` → `uint256` - Calculate current reward
- `calculateStakingLastReward(uint256 serviceId)` → `uint256` - Calculate last reward
- `getNextRewardCheckpointTimestamp()` → `uint256` - When next checkpoint occurs

### View Functions - Configuration

- `stakingToken()` → `address` - The ERC20 token used for staking
- `serviceRegistry()` → `address` - Service registry contract address
- `serviceRegistryTokenUtility()` → `address` - Service registry token utility contract
- `activityChecker()` → `address` - Activity checker contract address
- `rewardsPerSecond()` → `uint256` - Reward rate per second
- `minStakingDeposit()` → `uint256` - Minimum stake amount required
- `minStakingDuration()` → `uint256` - Minimum staking period
- `maxNumServices()` → `uint256` - Maximum services that can stake
- `maxNumInactivityPeriods()` → `uint256` - Maximum allowed inactivity periods
- `maxInactivityDuration()` → `uint256` - Max allowed inactivity duration
- `livenessPeriod()` → `uint256` - Liveness check period
- `numAgentInstances()` → `uint256` - Number of agent instances
- `threshold()` → `uint256` - Threshold value
- `timeForEmissions()` → `uint256` - Time for emissions
- `emissionsAmount()` → `uint256` - Emissions amount
- `epochCounter()` → `uint256` - Current epoch counter
- `tsCheckpoint()` → `uint256` - Last checkpoint timestamp

### View Functions - Metadata

- `VERSION()` → `string` - Contract version
- `configHash()` → `bytes32` - Configuration hash
- `proxyHash()` → `bytes32` - Proxy hash
- `metadataHash()` → `bytes32` - Metadata hash

### Other Functions

- `initialize(StakingParams, address, address)` - Initialize the staking contract
- `onERC721Received(address, address, uint256, bytes)` → `bytes4` - ERC721 receiver hook
- `setServiceIds(uint256)` → `uint256` - Set service IDs
- `agentIds(uint256)` → `uint256` - Get agent ID at index
- `mapServiceInfo(uint256)` → `(address, address, uint256, uint256, uint256)` - Get service info mapping

## Common Usage Patterns

1. **Stake a service:** Call `stake(serviceId)`
2. **Check rewards:** Call `calculateStakingReward(serviceId)`
3. **Claim rewards:** Call `claim(serviceId)` or `checkpointAndClaim(serviceId)`
4. **Unstake:** Call `unstake(serviceId)`
5. **View all staked services:** Call `getServiceIds()`
6. **Check staking parameters:** Call configuration view functions like `minStakingDeposit()`, `rewardsPerSecond()`, etc.

## Notes

- The contract uses a proxy pattern, so all calls (except `getImplementation()`) are forwarded to the implementation contract
- Most state-modifying functions require the caller to be the service owner or have appropriate permissions
- Rewards are calculated based on time staked and the `rewardsPerSecond()` rate
- Services must meet minimum staking requirements defined in the configuration
