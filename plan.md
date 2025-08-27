# EAS Attestation Wrapper for QuorumTracker Implementation Plan

## Overview

Implement a minimal EAS QuorumTracker contract that fulfills the IQuorumTracker interface required by Autonolas QuorumStakingTokenActivityChecker. The contract will maintain simple counters for three activity types (votes cast, opportunities considered, no opportunities) without complex on-chain logic.

## Current State Analysis

The quorum-ai system currently creates EAS attestations for successful Snapshot votes on Base network through `SafeService`. The system needs to track additional activity types and expose aggregated statistics through the IQuorumTracker interface.

### Key Discoveries:
- EAS integration exists in `backend/services/safe_service.py:436-563` for vote attestations
- Current schema only tracks successful votes
- All blockchain operations go through Safe multisig on Base network
- IQuorumTracker requires exactly 3 statistics: `[votes_cast, opportunities_considered, no_opportunities]`
- No existing Solidity contracts in the codebase

## Desired End State

A minimal QuorumTracker contract deployed on Base that:
- Implements `getVotingStats(address multisig)` returning a 3-element uint256 array
- Maintains simple counters per multisig address for each activity type
- Accepts registration calls from the backend to increment counters
- Provides gas-efficient read-only queries

### Verification Criteria:
- Contract written and deployed on local testnet using Forge
- Backend successfully registers all three activity types
- QuorumStakingTokenActivityChecker can query statistics
- System maintains backward compatibility with existing vote attestations

## What We're NOT Doing

- NOT implementing complex on-chain attestation querying or categorization
- NOT storing attestation UIDs or full data on-chain
- NOT implementing batch operations initially
- NOT creating parallel testing infrastructure with Foundry
- NOT modifying existing vote attestation flow

## Implementation Approach

Deploy a minimal counter contract and extend the backend to track additional activity types. Use existing service patterns and testing infrastructure to minimize complexity.

## Phase 1: Minimal Contract & Backend Integration

### Overview
Create a simple counter contract and integrate it with the existing backend services in a single coordinated effort.

### Changes Required:

#### 1. Create Minimal QuorumTracker Contract
**File**: `contracts/src/QuorumTracker.sol` (new)
**Changes**: 
```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import "@openzeppelin/contracts/access/Ownable.sol";

/**
 * @title IQuorumTracker
 * @dev Interface for the QuorumTracker contract required by Autonolas.
 */
interface IQuorumTracker {
    /**
     * @notice Gets the voting statistics for a given multisig address.
     * @param multisig The address of the multisig to get stats for.
     * @return A 3-element array of uint256 containing the stats.
     */
    function getVotingStats(address multisig) external view returns (uint256[] memory);
}

/**
 * @title QuorumTracker
 * @dev A contract to track voting and proposal consideration activity for multisig addresses.
 * This contract is owned and can only be updated by the owner (the backend service).
 */
contract QuorumTracker is IQuorumTracker, Ownable {
    // --- Constants ---
    uint8 public constant VOTES_CAST = 0;
    uint8 public constant OPPORTUNITIES_CONSIDERED = 1;
    uint8 public constant NO_OPPORTUNITIES = 2;

    // --- State ---
    /// @dev Stores the activity stats for each multisig address.
    /// The array indices correspond to the activity types defined in the constants.
    mapping(address => uint256[3]) public stats;

    // --- Constructor ---
    /**
     * @dev Sets the initial owner of the contract.
     * @param initialOwner The address of the initial owner.
     */
    constructor(address initialOwner) Ownable(initialOwner) {}

    // --- External Functions ---
    /**
     * @notice Registers an activity for a given multisig address.
     * @dev This function can only be called by the owner of the contract.
     *      It increments the counter for the specified activity type.
     * @param multisig The address of the multisig to register activity for.
     * @param activityType The type of activity to register. Must be 0, 1, or 2.
     */
    function register(address multisig, uint8 activityType) external onlyOwner {
        require(activityType <= NO_OPPORTUNITIES, "QuorumTracker: Invalid activity type");
        stats[multisig][activityType]++;
    }

    /**
     * @notice Gets the voting statistics for a given multisig address.
     * @param multisig The address of the multisig to get stats for.
     * @return result A 3-element array of uint256 containing the stats:
     *         - Index 0: Votes cast
     *         - Index 1: Opportunities considered
     *         - Index 2: No opportunities
     */
    function getVotingStats(address multisig) external view override returns (uint256[] memory result) {
        result = new uint256[](3);
        result[VOTES_CAST] = stats[multisig][VOTES_CAST];
        result[OPPORTUNITIES_CONSIDERED] = stats[multisig][OPPORTUNITIES_CONSIDERED];
        result[NO_OPPORTUNITIES] = stats[multisig][NO_OPPORTUNITIES];
    }
}
```

#### 2. Create QuorumTracker Service
**File**: `backend/services/quorum_tracker_service.py` (new)
**Changes**:
- Create service class following existing patterns
- Use dependency injection with SafeService
- Implement `register_activity()` method
- Add Pearl-compliant logging

```python
from typing import Dict, Any
from services.safe_service import SafeService
from logging_config import setup_pearl_logger

class QuorumTrackerService:
    """Service for QuorumTracker contract interactions."""
    
    def __init__(self, safe_service: SafeService):
        self.logger = setup_pearl_logger(__name__)
        self.safe_service = safe_service
        
    async def register_activity(
        self, 
        multisig_address: str, 
        activity_type: int
    ) -> Dict[str, Any]:
        """Register activity with QuorumTracker contract."""
        # Implementation using safe_service for transaction submission
        pass
```

#### 3. Extend Data Models
**File**: `backend/models.py`
**Changes**:
- Add activity type enum
- Extend existing validation patterns

```python
from enum import IntEnum

class ActivityType(IntEnum):
    VOTE_CAST = 0
    OPPORTUNITY_CONSIDERED = 1
    NO_OPPORTUNITY = 2
```

#### 4. Update Agent Run Service
**File**: `backend/services/agent_run_service.py`
**Changes**:
- Track all three activity types during proposal processing
- Call QuorumTrackerService to register activities
- Maintain existing attestation flow for votes

#### 5. Add Configuration
**File**: `backend/config.py`
**Changes**:
```python
quorum_tracker_address: Optional[str] = Field(
    default=None,
    alias="QUORUM_TRACKER_ADDRESS",
    description="QuorumTracker contract address on local testnet",
)

quorum_tracker_owner: Optional[str] = Field(
    default=None,
    alias="QUORUM_TRACKER_OWNER",
    description="Owner address for QuorumTracker contract (backend service wallet)",
)

@field_validator("quorum_tracker_address", "quorum_tracker_owner", mode="before")
@classmethod
def validate_tracker_addresses(cls, v):
    if v and not Web3.is_address(v):
        raise ValueError(f"Invalid contract address: {v}")
    return Web3.to_checksum_address(v) if v else None
```

#### 6. Add Contract ABI
**File**: `backend/abi/quorum_tracker.json` (new)
**Changes**:
- Add compiled ABI for QuorumTracker contract
- Follow existing ABI file pattern

### Success Criteria:

#### Automated Verification:
- [x] Backend tests pass: `uv run pytest backend/tests/` (12 QuorumTracker tests passing)
- [x] New service tests pass: `uv run pytest backend/tests/test_quorum_tracker_service.py`
- [x] Configuration validation passes: `uv run pytest backend/tests/test_quorum_tracker_config.py`

#### Implementation Status:
- [x] **COMPLETED** - Created ActivityType enum in `backend/models.py` with three values (VOTE_CAST=0, OPPORTUNITY_CONSIDERED=1, NO_OPPORTUNITY=2)
- [x] **COMPLETED** - Extended backend configuration in `backend/config.py` with QuorumTracker address and owner fields including Web3 address validation
- [x] **COMPLETED** - Created QuorumTrackerService in `backend/services/quorum_tracker_service.py` following existing patterns with SafeService dependency injection and Pearl-compliant logging
- [x] **COMPLETED** - Added QuorumTracker ABI file at `backend/abi/quorum_tracker.json`
- [x] **COMPLETED** - All tests pass with proper mocking and validation

**Implementation Date**: August 26, 2025

#### Manual Verification (Next Phase):
- [ ] Contract deployed to local testnet with proper ownership
- [ ] Activities registered successfully by authorized owner only
- [ ] Statistics queryable through contract

---

## Phase 2: Testing & Deployment

### Overview
Deploy the contract to a local testnet using Forge and validate the complete integration with Solidity-based tests.

### Foundry Project Structure
We will adopt the standard Foundry directory structure for all smart contract development.

```
contracts/
├── src/                      # Smart contracts
│   └── QuorumTracker.sol
├── test/                     # Test files
│   └── QuorumTracker.t.sol
├── script/                   # Deployment scripts
│   └── Deploy.s.sol
├── lib/                      # Dependencies (OpenZeppelin)
└── foundry.toml              # Foundry configuration
```

### Changes Required:

#### 1. Create Foundry Project
- Initialize a new Foundry project in a `contracts/` directory.
- Install OpenZeppelin contracts: `forge install OpenZeppelin/openzeppelin-contracts`
- Configure remappings in `foundry.toml`:
```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc = "0.8.24"

remappings = [
    "@openzeppelin/=lib/openzeppelin-contracts/"
]
```

#### 2. Contract Deployment Script (Forge)
**File**: `contracts/script/Deploy.s.sol` (new)
**Changes**:
- Create a deployment script using `forge-std/Script.sol`.
- The script will deploy the `QuorumTracker` contract with proper ownership.
- It will log the deployed contract address.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {QuorumTracker} from "../src/QuorumTracker.sol";

contract DeployScript is Script {
    function run() public returns (QuorumTracker) {
        // Get the deployer's private key from environment
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address owner = vm.envAddress("QUORUM_TRACKER_OWNER");
        
        vm.startBroadcast(deployerPrivateKey);
        QuorumTracker quorumTracker = new QuorumTracker(owner);
        console.log("QuorumTracker deployed to:", address(quorumTracker));
        console.log("Contract owner:", owner);
        vm.stopBroadcast();
        
        return quorumTracker;
    }
}
```

#### 3. Contract Tests (Forge)
**File**: `contracts/test/QuorumTracker.t.sol` (new)
**Changes**:
- Write comprehensive unit and fuzz tests for the `QuorumTracker` contract.
- Test access control, activity registration, and statistics retrieval.

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

import {Test, console} from "forge-std/Test.sol";
import {QuorumTracker} from "../src/QuorumTracker.sol";

contract QuorumTrackerTest is Test {
    QuorumTracker public quorumTracker;
    address public owner = makeAddr("owner");
    address public multisig = makeAddr("multisig");
    address public unauthorized = makeAddr("unauthorized");

    function setUp() public {
        vm.prank(owner);
        quorumTracker = new QuorumTracker(owner);
    }

    function test_RegisterActivity_AsOwner() public {
        vm.prank(owner);
        quorumTracker.register(multisig, 0);
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisig);
        assertEq(stats[0], 1, "Votes cast should be 1");
        assertEq(stats[1], 0, "Opportunities considered should be 0");
        assertEq(stats[2], 0, "No opportunities should be 0");
    }

    function test_RevertWhen_RegisterActivity_NotOwner() public {
        vm.prank(unauthorized);
        vm.expectRevert();
        quorumTracker.register(multisig, 0);
    }

    function testFuzz_RegisterMultipleActivities(uint8 activityType) public {
        vm.assume(activityType < 3);
        
        vm.prank(owner);
        quorumTracker.register(multisig, activityType);
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisig);
        assertEq(stats[activityType], 1, "Activity should be incremented");
    }

    function test_RevertWhen_InvalidActivityType() public {
        vm.prank(owner);
        vm.expectRevert("QuorumTracker: Invalid activity type");
        quorumTracker.register(multisig, 3);
    }

    function test_MultipleRegistrations() public {
        vm.startPrank(owner);
        
        // Register multiple activities
        quorumTracker.register(multisig, 0); // Vote cast
        quorumTracker.register(multisig, 0); // Another vote cast
        quorumTracker.register(multisig, 1); // Opportunity considered
        quorumTracker.register(multisig, 2); // No opportunity
        
        vm.stopPrank();
        
        uint256[] memory stats = quorumTracker.getVotingStats(multisig);
        assertEq(stats[0], 2, "Votes cast should be 2");
        assertEq(stats[1], 1, "Opportunities considered should be 1");
        assertEq(stats[2], 1, "No opportunities should be 1");
    }

    function test_DifferentMultisigs() public {
        address multisig2 = makeAddr("multisig2");
        
        vm.startPrank(owner);
        quorumTracker.register(multisig, 0);
        quorumTracker.register(multisig2, 1);
        vm.stopPrank();
        
        uint256[] memory stats1 = quorumTracker.getVotingStats(multisig);
        uint256[] memory stats2 = quorumTracker.getVotingStats(multisig2);
        
        assertEq(stats1[0], 1, "Multisig1 votes cast should be 1");
        assertEq(stats2[1], 1, "Multisig2 opportunities considered should be 1");
    }
}
```

#### 4. Local Testnet Deployment Commands
```bash
# Start local testnet (in a separate terminal)
anvil --fork-url $BASE_RPC_URL --chain-id 31337

# Deploy contract to local testnet
cd contracts
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast

# Run tests
forge test -vvv

# Generate gas report
forge test --gas-report
```

#### 5. Update Environment Configuration
**File**: `.env.example`
**Changes**:
```bash
# QuorumTracker Configuration
QUORUM_TRACKER_ADDRESS=0x...  # Deployed contract address on local testnet
QUORUM_TRACKER_OWNER=0x...    # Owner address (backend service wallet)
PRIVATE_KEY=0x...              # Private key for deployment (only for local testing)
BASE_RPC_URL=https://...       # Base RPC URL for forking
```

### Success Criteria:

#### Automated Verification:
- [ ] Contract compiles: `forge build`
- [ ] All Solidity tests pass: `forge test`
- [ ] Gas usage is acceptable: `forge test --gas-report`
- [ ] Coverage is comprehensive: `forge coverage`
- [ ] Integration tests pass: `uv run pytest backend/tests/test_quorum_tracker_integration.py`

#### Manual Verification:
- [ ] Contract deployed successfully to local testnet
- [ ] Only authorized owner can register activities
- [ ] Complete agent run creates all activity types
- [ ] QuorumStakingTokenActivityChecker integration successful

---

## Testing Strategy

### Solidity Tests (Forge):
- Unit tests for all contract functions
- Access control verification
- Edge case handling (invalid activity types)
- Fuzz testing for robustness
- Gas optimization verification

### Integration Tests (Python):
- Service method testing with mocks
- Configuration validation tests
- End-to-end activity registration flow
- Statistics retrieval verification

### Local Testnet Testing:
1. Start Anvil with Base fork: `anvil --fork-url $BASE_RPC_URL`
2. Deploy contract: `forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast`
3. Configure backend with contract address
4. Run agent to create activities
5. Query contract for statistics using `cast call`
6. Verify integration with QuorumStakingTokenActivityChecker

### Manual Testing Steps:
1. Deploy contract to local testnet
2. Configure contract address and owner in environment
3. Run agent to create activities
4. Query contract for statistics
5. Verify with QuorumStakingTokenActivityChecker

## Performance Considerations

- Simple counter increments minimize gas costs
- View function for statistics query (zero gas)
- No complex on-chain logic or storage
- Access control adds minimal overhead

## Migration Notes

- Existing vote attestations unchanged
- New activity tracking is additive
- Contract deployment independent of existing flow
- Feature flag via QUORUM_TRACKER_ADDRESS environment variable

## References

- Original ticket: `https://github.com/Backland-Labs/quorum-ai/issues/173`
- Related research: `research/eas-quorum-tracker-wrapper.md`
- Autonolas contract: `https://github.com/valory-xyz/autonolas-staking-programmes/blob/96b71209c1a36dd0706c82bd2673ba338e4d4eee/contracts/externals/backland/QuorumStakingTokenActivityChecker.sol#L26`