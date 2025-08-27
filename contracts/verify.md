# QuorumTracker Contract Verification Guide

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

# Run tests
forge test -vvv

# Generate gas report
forge test --gas-report

# Check coverage
forge coverage
```

## Expected Results

### Contract Compilation
- ✅ QuorumTracker.sol compiles without errors
- ✅ Uses Solidity 0.8.24 as specified
- ✅ Implements IQuorumTracker interface
- ✅ Inherits from OpenZeppelin Ownable

### Test Results
The comprehensive test suite should pass all tests including:

1. **Constructor Tests**
   - ✅ Sets owner correctly
   - ✅ Rejects zero address as owner

2. **Activity Registration Tests**  
   - ✅ Owner can register all three activity types
   - ✅ Non-owner registration is rejected
   - ✅ Invalid activity types (>2) are rejected

3. **Statistics Retrieval Tests**
   - ✅ Returns correct 3-element array
   - ✅ Unregistered multisigs return zeros
   - ✅ Public access for statistics reading

4. **Multiple Operations Tests**
   - ✅ Multiple registrations increment correctly
   - ✅ Different multisigs have independent stats
   - ✅ State consistency after many operations

5. **Fuzz Tests**
   - ✅ Valid activity types work correctly
   - ✅ Invalid activity types are rejected
   - ✅ Multiple registrations with bounds testing

6. **Gas Optimization Tests**
   - ✅ Registration uses reasonable gas
   - ✅ Statistics retrieval is gas efficient

### Deployment Script
- ✅ Deploy.s.sol compiles and runs
- ✅ Properly sets contract owner
- ✅ Logs deployment information
- ✅ Verifies deployment success

## ABI Compatibility

The generated contract ABI should match the existing `backend/abi/quorum_tracker.json`:

- ✅ `constructor(address initialOwner)`
- ✅ `register(address multisig, uint8 activityType)` 
- ✅ `getVotingStats(address multisig) returns (uint256[] result)`
- ✅ Constants: `VOTES_CAST`, `OPPORTUNITIES_CONSIDERED`, `NO_OPPORTUNITIES`
- ✅ Public `stats` mapping access

## Manual Testing Commands

After deployment to local testnet:

```bash
# Start local testnet
anvil --fork-url $BASE_RPC_URL --chain-id 31337

# Deploy contract
PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \
QUORUM_TRACKER_OWNER=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast

# Test registration (owner only)
cast send <DEPLOYED_ADDRESS> "register(address,uint8)" <MULTISIG_ADDRESS> 0 \
  --private-key $PRIVATE_KEY --rpc-url http://localhost:8545

# Query statistics
cast call <DEPLOYED_ADDRESS> "getVotingStats(address)" <MULTISIG_ADDRESS> \
  --rpc-url http://localhost:8545
```

## Integration with Backend

Once deployed, update the backend configuration:

```bash
# In .env file
QUORUM_TRACKER_ADDRESS=0x...  # Deployed contract address
QUORUM_TRACKER_OWNER=0x...    # Owner address (backend service wallet)
```

The backend should now be able to:
- ✅ Register activities through QuorumTrackerService
- ✅ Query statistics for multisig addresses
- ✅ Integrate with agent run workflow