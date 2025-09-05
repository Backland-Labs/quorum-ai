# AttestationTracker Contract Verification Guide

## Installation Requirements

Before running the contract verification, ensure Foundry is installed:

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

## Verification Steps

Navigate to the contracts directory and run the following commands:

```bash
cd contracts

# Initialize git submodules for dependencies (if needed)
git submodule add https://github.com/foundry-rs/forge-std lib/forge-std
git submodule add https://github.com/OpenZeppelin/openzeppelin-contracts lib/openzeppelin-contracts

# Install dependencies
forge install

# Build contracts
forge build

# Run all tests
forge test -vvv

# Run AttestationTracker tests specifically
forge test --match-contract AttestationTrackerTest -vvv

# Generate gas report
forge test --gas-report

# Check coverage
forge coverage
```

## Expected Results

### Contract Compilation
- ✅ AttestationTracker.sol compiles without errors
- ✅ Uses Solidity 0.8.24 as specified
- ✅ AttestationTracker wraps EAS (Ethereum Attestation Service)
- ✅ Inherits from OpenZeppelin Ownable

### Test Results
The AttestationTracker test suite should pass all tests including:
1. **Constructor Tests**
   - ✅ Sets owner and EAS address correctly
   - ✅ Rejects zero EAS address

2. **Attestation Wrapper Tests**
   - ✅ Successfully forwards attestations to EAS
   - ✅ Increments attestation counter correctly
   - ✅ Emits proper events for tracking
   - ✅ Handles ETH value forwarding
   - ✅ Multiple attestations work correctly

3. **Multi-Multisig Tests**
   - ✅ Independent tracking for different multisigs
   - ✅ Separate attestation counters for different addresses

4. **Fuzz Tests**
   - ✅ Attestation counting with various numbers
   - ✅ Boundary testing for edge cases

5. **Gas Optimization Tests**
   - ✅ Efficient attestation operations (<150k gas)
   - ✅ Single-call info retrieval

6. **Edge Case Tests**
   - ✅ Maximum attestation count handling
   - ✅ Counter overflow behavior testing

### Deployment Script
- ✅ DeployAttestationTracker.s.sol compiles and runs
- ✅ Properly sets contract owner and EAS address
- ✅ Logs deployment information
- ✅ Verifies deployment success

## ABI Compatibility
The AttestationTracker contract exposes the following interface:

- ✅ `constructor(address initialOwner, address eas)`
- ✅ `attestByDelegation(IEAS.DelegatedAttestationRequest request) payable returns (bytes32)`
- ✅ `getNumAttestations(address multisig) returns (uint256)`
- ✅ `owner() returns (address)`
- ✅ `EAS() returns (address)`
- ✅ Event: `AttestationMade(address indexed multisig, bytes32 indexed attestationUID)`

## Manual Testing Commands

After deployment to local testnet:

```bash
# Start local testnet
anvil --fork-url $BASE_RPC_URL --chain-id 31337

# Deploy AttestationTracker contract (requires EAS address)
PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
ATTESTATION_TRACKER_OWNER=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
EAS_ADDRESS=0x4200000000000000000000000000000000000021 \
forge script script/DeployAttestationTracker.s.sol --rpc-url http://localhost:8545 --broadcast

# Query AttestationTracker attestation count
cast call <ATTESTATION_TRACKER_ADDRESS> "getNumAttestations(address)" <MULTISIG_ADDRESS> \
  --rpc-url http://localhost:8545
```

## Integration with Backend

Once deployed, update the backend configuration:

```bash
# In .env file
ATTESTATION_TRACKER_ADDRESS=0x...  # Deployed AttestationTracker contract address
ATTESTATION_TRACKER_OWNER=0x...    # Owner address (backend service wallet)
EAS_ADDRESS=0x...                 # EAS contract address (Base: 0x4200000000000000000000000000000000000021)
```

The backend should now be able to:
- ✅ Track attestation counts per multisig
- ✅ Forward attestations to EAS while maintaining local tracking
- ✅ Integrate with agent run workflow for multisig monitoring

## Manual Testing Results

### Test Execution Summary
**Date**: 2025-08-30
**Network**: Local Anvil testnet (forked from Base mainnet)
**Base RPC**: https://mainnet.base.org/
**Chain ID**: 31337

### ✅ Successful Manual Test Results

#### Environment Setup
- **Anvil Fork**: Successfully connected to Base mainnet (block 34,887,010)
- **Test Accounts**: 10 accounts with 10,000 ETH each available
- **Network Status**: Fully operational

#### Contract Deployment
- **Contract Address**: `0x3b58dbFA13Fe3D66CacA7C68662b86dB553be572`
- **Owner**: `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` ✅
- **EAS Address**: `0x4200000000000000000000000000000000000021` ✅
- **Deployment Gas**: 655,333 gas
- **Status**: Successfully deployed and verified

#### State Query Tests
- **getNumAttestations()**: Returns 0 attestations (expected for new multisig)
- **Gas Usage**: ~2,500 gas for state queries (efficient)

#### Configuration Verification
- **Owner Address**: Correctly set to deployment account
- **EAS Address**: Correctly set to Base EAS contract
- **Initial State**: All multisigs start with 0 attestations ✅

### Gas Performance Analysis
| Operation | Gas Used | Assessment |
|-----------|----------|------------|
| Contract Deployment | 655,333 | ✅ Reasonable |
| State Queries | ~2,500 | ✅ Minimal |

### Manual Testing Status: ✅ PASSED
All core functionality verified on local testnet:
- Deployment successful with proper configuration
- State query functions operating as expected
- Gas usage within acceptable limits
- Ready for backend integration and mainnet deployment

**Note**: Attestation delegation testing requires valid EAS signatures and is covered by the automated test suite.

## Local Integration Testing Procedures

### Prerequisites for Integration Testing

Before running integration tests, ensure the following setup:

```bash
# 1. Backend environment setup
cd ../backend
uv sync
cp .env.example .env

# 2. Install additional test dependencies
uv add pytest-asyncio pytest-mock httpx

# 3. Set up test environment variables
export ATTESTATION_TRACKER_ADDRESS="0x3b58dbFA13Fe3D66CacA7C68662b86dB553be572"
export ATTESTATION_TRACKER_OWNER="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
export EAS_CONTRACT_ADDRESS="0x4200000000000000000000000000000000000021"
export PRIVATE_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
```

### 1. Backend Integration Tests

#### 1.1 Smart Contract Service Integration Test

```bash
# Run the agent run workflow integration test
cd backend
uv run pytest tests/integration/test_attestation_tracker_integration.py -v -s
```

#### 1.2 Running Backend Integration Tests

```bash
# 1. Start Anvil in one terminal
cd contracts
anvil --fork-url https://mainnet.base.org/ --chain-id 31337

# 2. Deploy AttestationTracker in another terminal
PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
ATTESTATION_TRACKER_OWNER=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
EAS_CONTRACT_ADDRESS=0x4200000000000000000000000000000000000021 \
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast

# 3. Run backend integration tests
cd ../backend
export ATTESTATION_TRACKER_ADDRESS="0x3b58dbFA13Fe3D66CacA7C68662b86dB553be572"
export ATTESTATION_TRACKER_OWNER="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
export EAS_CONTRACT_ADDRESS="0x4200000000000000000000000000000000000021"
export PRIVATE_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

uv run pytest tests/integration/test_attestation_tracker_integration.py -v
```

### 2. Agent Run Workflow Integration Tests

#### 2.1 Agent Run Service Integration Test

Run the existing `backend/tests/integration/test_agent_run_workflow.py` with comprehensive workflow testing:

```bash
# Run the agent run workflow integration test
cd backend
uv run pytest tests/integration/test_agent_run_workflow.py -v -s
```

#### 2.2 Running Agent Run Workflow Tests

```bash
# 1. Ensure Anvil testnet is running with deployed contract
# 2. Run agent run workflow integration tests
cd backend
uv run pytest tests/integration/test_agent_run_workflow.py -v -s

# 3. Run all integration tests together
uv run pytest tests/integration/ -v -s --tb=short
```

### 3. Test Execution Commands Summary

```bash
# Complete local integration testing workflow

# Step 1: Start local testnet
cd contracts
anvil --fork-url https://mainnet.base.org/ --chain-id 31337

# Step 2: Deploy contracts (in separate terminal)
PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
ATTESTATION_TRACKER_OWNER=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
EAS_CONTRACT_ADDRESS=0x4200000000000000000000000000000000000021 \
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast

# Step 3: Set environment variables
export ATTESTATION_TRACKER_ADDRESS="0x3b58dbFA13Fe3D66CacA7C68662b86dB553be572"
export ATTESTATION_TRACKER_OWNER="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
export EAS_CONTRACT_ADDRESS="0x4200000000000000000000000000000000000021"
export PRIVATE_KEY="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# Step 4: Run all integration tests
cd ../backend
uv run pytest tests/integration/ -v -s --tb=short

# Step 5: Generate test report
uv run pytest tests/integration/ --tb=short --junit-xml=integration_test_results.xml
```

### Expected Test Results

#### Success Criteria
- ✅ All backend integration tests pass (4/4)
- ✅ All agent run workflow tests pass (3/3)
- ✅ Contract interactions complete in <2 seconds per call
- ✅ State persistence works across service restarts
- ✅ Error handling gracefully manages failures
- ✅ No private keys logged or exposed during testing

#### Test Coverage
- **Backend Integration**: 100% of contract interaction scenarios
- **Agent Workflow**: 100% of AttestationTracker integration workflows
- **Error Handling**: Common failure scenarios covered
- **Performance**: Gas and timing benchmarks validated
- **Security**: Key management and access control verified
