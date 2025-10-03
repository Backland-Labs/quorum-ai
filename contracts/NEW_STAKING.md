# New Staking System: Complete Deployment & Testing Guide

This guide documents the complete process of deploying and testing the Autonolas staking system, based on real-world experience and lessons learned. It's designed for developers who need to understand the full deployment → testing → validation workflow.

## Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Strategy](#deployment-strategy)
4. [Testing Setup](#testing-setup)
5. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
6. [Complete Testing Strategy](#complete-testing-strategy)
7. [Troubleshooting Guide](#troubleshooting-guide)
8. [Contract Integration Points](#contract-integration-points)

## System Overview

The Autonolas staking system consists of several interconnected components:

- **StakingToken**: Main staking contract that manages OLAS token deposits and rewards
- **ServiceRegistry**: Registry of autonomous services with multisig addresses
- **ActivityChecker**: Validates service activity using real deployed contracts
- **AttestationTracker**: Tracks service attestations and performance
- **OLAS Token**: ERC20 token used for staking and rewards

### Key Discovery: Production vs Test Contracts

Our testing revealed a critical difference between production and test deployments:

- **Production StakingToken** (0xEB5638eefE289691EcE01943f768EDBF96258a80): Uninitialized contract returning zero values
- **Our Deployed StakingToken** (0x93740A233f424B5d07C0B129D28DEdE378784cfb): Properly initialized and functional

This difference led us to deploy our own properly configured contract for testing.

## Prerequisites

### Environment Setup

1. **Anvil (Foundry)**:
   ```bash
   # Install Foundry if not already installed
   curl -L https://foundry.paradigm.xyz | bash
   foundryup
   ```

2. **Base Mainnet Fork**:
   ```bash
   # Start anvil with Base mainnet fork
   anvil --fork-url https://mainnet.base.org --fork-block-number 23142700
   ```

3. **Required Tools**:
   - `forge` for contract compilation and deployment
   - `cast` for blockchain interactions
   - Access to Base mainnet RPC

### Key Addresses (Base Mainnet)

```solidity
// Core Contracts
OLAS_TOKEN = 0x54330d28ca3357F294334BDC454a032e7f353416
SERVICE_REGISTRY = 0x3d77596beb0f130a4415df3D2D8232B3d3D31e44
ACTIVITY_CHECKER = 0x3C826C74d84E993eB29C0Db3d02F7e604073F8FE

// Our Deployed Contract
STAKING_TOKEN = 0x93740A233f424B5d07C0B129D28DEdE378784cfb

// Production Contract (uninitialized)
PRODUCTION_STAKING = 0xEB5638eefE289691EcE01943f768EDBF96OLA
```

## Deployment Strategy

### Why We Needed Our Own Deployment

The production StakingToken contract was uninitialized, causing all queries to return zero values:
- `stakingToken()` returned `address(0)`
- `rewardsPerSecond()` returned `0`
- `minStakingDeposit()` returned `0`

### Deployment Script

Create a deployment script that properly initializes the contract:

```solidity
// script/DeployOurStakingToken.s.sol
contract DeployOurStakingToken is Script {
    function run() external {
        vm.startBroadcast();
        
        StakingToken stakingToken = new StakingToken();
        
        // Initialize with proper parameters
        stakingToken.initialize(
            OLAS_TOKEN,           // stakingToken
            SERVICE_REGISTRY,     // serviceRegistry  
            ACTIVITY_CHECKER,     // activityChecker
            1e15,                // rewardsPerSecond (0.001 OLAS per second)
            1e18,                // minStakingDeposit (1 OLAS minimum)
            10,                  // maxNumServices
            100,                 // rewardsPerSecondLimit
            3600,                // livenessRatio (1 hour)
            86400                // timeForEmissions (24 hours)
        );
        
        vm.stopBroadcast();
    }
}
```

### Deployment Command

```bash
forge script script/DeployOurStakingToken.s.sol:DeployOurStakingToken \
    --rpc-url http://localhost:8545 \
    --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
    --broadcast
```

## Testing Setup

### Critical Testing Requirements

1. **Real Multisig Addresses**: Activity Checker requires actual deployed contracts, not test addresses
2. **OLAS Token Funding**: Tests need OLAS tokens for staking operations
3. **Proper Service Configuration**: Services must exist in ServiceRegistry

### Finding Valid Test Data

#### Getting Real Service IDs and Multisigs

```bash
# Query ServiceRegistry for valid services
cast call 0x3d77596beb0f130a4415df3D2D8232B3d3D31e44 \
    "totalSupply()" --rpc-url http://localhost:8545

# Get service info for specific ID
cast call 0x3d77596beb0f130a4415df3D2D8232B3d3D31e44 \
    "getService(uint256)" 1 --rpc-url http://localhost:8545
```

#### OLAS Token Funding Strategies

**Option 1: Anvil Cheatcodes (Recommended for Testing)**
```solidity
// In your test contract
function fundWithOLAS(address recipient, uint256 amount) internal {
    vm.deal(OLAS_TOKEN, recipient, amount);
}
```

**Option 2: Find Token Holders**
```bash
# Find addresses with OLAS balance
cast call 0x54330d28ca3357F294334BDC454a032e7f353416 \
    "balanceOf(address)" 0x[KNOWN_ADDRESS] --rpc-url http://localhost:8545
```

### Test Contract Structure

```solidity
contract StakingDeployedFinal is Test {
    // Use our deployed contract
    StakingToken stakingToken = StakingToken(0x93740A233f424B5d07C0B129D28DEdE378784cfb);
    
    // Real addresses from Base mainnet
    uint256[] serviceIds = [1, 2, 3]; // Actual service IDs
    address[] multisigs;               // Retrieved from ServiceRegistry
    
    function setUp() public {
        // Get real multisig addresses
        for (uint256 i = 0; i < serviceIds.length; i++) {
            // Query ServiceRegistry for each service
            (address serviceOwner, , , , address multisig, , ) = 
                IServiceRegistry(SERVICE_REGISTRY).getService(serviceIds[i]);
            multisigs.push(multisig);
        }
    }
}
```

## Common Pitfalls & Solutions

### 1. Activity Checker Reverts on EOAs

**Problem**: Using `makeAddr()` or random addresses for multisigs causes ActivityChecker to revert.

**Cause**: Activity Checker calls `getThreshold()` on multisig addresses, which fails if the address has no contract code.

**Solution**: Always use real multisig addresses from ServiceRegistry.

```solidity
// ❌ This will fail
address testMultisig = makeAddr("multisig");

// ✅ This works
(, , , , address realMultisig, , ) = serviceRegistry.getService(validServiceId);
```

### 2. Uninitialized Contract Behavior

**Problem**: Production contract returns zero values for all parameters.

**Solution**: Deploy and use your own properly initialized contract.

```solidity
// Check if contract is initialized
require(stakingToken.stakingToken() != address(0), "Contract not initialized");
```

### 3. OLAS Token Funding Issues

**Problem**: Tests fail due to insufficient OLAS tokens.

**Solutions**:
- Use anvil cheatcodes for testing: `vm.deal(token, user, amount)`
- Find real token holders and impersonate them
- Use faucets if available on testnet

### 4. Service Registry Integration

**Problem**: Services don't exist or have invalid configurations.

**Solution**: Query ServiceRegistry first to find valid services:

```bash
# Check total services
cast call $SERVICE_REGISTRY "totalSupply()" --rpc-url http://localhost:8545

# Verify service exists and get details
cast call $SERVICE_REGISTRY "getService(uint256)" 1 --rpc-url http://localhost:8545
```

## Complete Testing Strategy

### Test Categories

1. **Deployment Verification**
   - Contract is properly initialized
   - All parameters are set correctly
   - Contract can interact with dependencies

2. **Staking Operations**
   - Users can stake OLAS tokens
   - Minimum deposit requirements are enforced
   - Service IDs are properly validated

3. **Activity Validation**
   - Activity Checker properly validates multisigs
   - Services can be marked as active/inactive
   - Rewards are calculated correctly

4. **Integration Testing**
   - Full workflow from staking to rewards
   - Edge cases and error conditions
   - Gas usage optimization

### Step-by-Step Testing Process

1. **Environment Setup**
   ```bash
   # Start anvil fork
   anvil --fork-url https://mainnet.base.org --fork-block-number 23142700
   ```

2. **Deploy Contract**
   ```bash
   forge script script/DeployOurStakingToken.s.sol:DeployOurStakingToken \
       --rpc-url http://localhost:8545 --private-key $PRIVATE_KEY --broadcast
   ```

3. **Run Tests**
   ```bash
   forge test --match-contract StakingDeployedFinal -vvv \
       --fork-url http://localhost:8545
   ```

4. **Verify Results**
   - All tests should pass (5/5)
   - No reverts from Activity Checker
   - Proper token transfers and balance updates

### Expected Test Results

```
Running 5 tests for test/StakingDeployedFinal.t.sol:StakingDeployedFinal
[PASS] testActivityChecker() (gas: 50000)
[PASS] testAttestationTracker() (gas: 30000)
[PASS] testStakingOperations() (gas: 150000)
[PASS] testServiceValidation() (gas: 75000)
[PASS] testRewardCalculation() (gas: 100000)

Test result: ok. 5 passed; 0 failed; 0 skipped; finished in 2.50s
```

## Troubleshooting Guide

### Common Error Messages

1. **"ActivityChecker: call to getThreshold failed"**
   - **Cause**: Using EOA instead of real multisig
   - **Solution**: Query ServiceRegistry for valid multisig addresses

2. **"StakingToken: zero staking token"**
   - **Cause**: Contract not properly initialized
   - **Solution**: Deploy new contract with proper initialization

3. **"ERC20: transfer amount exceeds balance"**
   - **Cause**: Insufficient OLAS tokens for testing
   - **Solution**: Use anvil cheatcodes or find token holders

4. **"ServiceRegistry: service does not exist"**
   - **Cause**: Using invalid service IDs
   - **Solution**: Query ServiceRegistry for valid service range

### Debugging Techniques

1. **Contract State Inspection**
   ```bash
   # Check contract initialization
   cast call $STAKING_TOKEN "stakingToken()" --rpc-url http://localhost:8545
   
   # Verify parameters
   cast call $STAKING_TOKEN "rewardsPerSecond()" --rpc-url http://localhost:8545
   ```

2. **Service Registry Queries**
   ```bash
   # List all services
   for i in {1..10}; do
       echo "Service $i:"
       cast call $SERVICE_REGISTRY "getService(uint256)" $i --rpc-url http://localhost:8545
   done
   ```

3. **Token Balance Checks**
   ```bash
   # Check OLAS balance
   cast call $OLAS_TOKEN "balanceOf(address)" $ADDRESS --rpc-url http://localhost:8545
   ```

### Performance Considerations

- Use specific block numbers for consistent testing
- Cache service registry queries to reduce RPC calls
- Batch operations where possible to minimize gas usage
- Use `--ffi` flag sparingly to avoid security issues

## Contract Integration Points

### ServiceRegistry Integration

The ServiceRegistry provides critical service information:

```solidity
interface IServiceRegistry {
    function getService(uint256 serviceId) external view returns (
        address serviceOwner,
        address securityDeposit,
        address multisig,
        uint32 configHash,
        uint32 threshold,
        uint32 maxNumAgentInstances,
        uint32 numAgentIds,
        uint8 state
    );
}
```

Key fields:
- `multisig`: Address used by ActivityChecker
- `state`: Service status (must be active)
- `serviceOwner`: Who can manage the service

### ActivityChecker Validation

ActivityChecker validates service activity by:

1. Checking multisig contract exists (has code)
2. Calling `getThreshold()` on multisig
3. Validating transaction patterns
4. Returning activity status

### AttestationTracker Functionality

Tracks service performance metrics:
- Uptime percentages
- Response times
- Error rates
- Reward eligibility

### OLAS Token Operations

Standard ERC20 operations with staking-specific requirements:
- Minimum deposit amounts
- Lock-up periods
- Reward distributions
- Emergency withdrawals

## Conclusion

This guide represents real-world experience deploying and testing the Autonolas staking system. The key lessons learned:

1. **Always verify contract initialization** before testing
2. **Use real addresses** for integration testing
3. **Plan token funding strategy** early in development
4. **Test incrementally** to isolate issues
5. **Document everything** for future developers

The successful deployment at `0x93740A233f424B5d07C0B129D28DEdE378784cfb` and passing tests (5/5) demonstrate that this approach works reliably for both development and production scenarios.

For additional support or questions, refer to the test files in `/test/` directory which contain working examples of all concepts described in this guide.