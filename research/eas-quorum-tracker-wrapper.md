---
date: 2025-08-26T17:30:38Z
researcher: Claude
git_commit: 788cc08f08d82899f3f2e9a78a1d950f8e7bf0b4
branch: develop
repository: quorum-ai
topic: "How to wrap EAS attestations in a Solidity contract for use as quorumTracker"
tags: [research, codebase, eas, solidity, quorum-tracker, attestations, governance]
status: complete
last_updated: 2025-08-26
last_updated_by: Claude
---

# Research: How to Wrap EAS Attestations in a Solidity Contract for Use as QuorumTracker

**Date**: 2025-08-26T17:30:38Z
**Researcher**: Claude
**Git Commit**: 788cc08f08d82899f3f2e9a78a1d950f8e7bf0b4
**Branch**: develop
**Repository**: quorum-ai

## Research Question
How can I wrap the EAS attestations in a Solidity contract to be used as quorumTracker in this contract: https://github.com/valory-xyz/autonolas-staking-programmes/blob/96b71209c1a36dd0706c82bd2673ba338e4d4eee/contracts/externals/backland/QuorumStakingTokenActivityChecker.sol#L26

## Summary
The QuorumStakingTokenActivityChecker requires a quorumTracker contract that implements the IQuorumTracker interface with a `getVotingStats(address multisig)` method returning four uint256 values. To wrap EAS attestations for this purpose, you need to create a Solidity contract that:

1. Connects to the EAS contract (0xA1207F3BBa224E2c9c3c6D5aF63D0eb1582Ce587 on Ethereum mainnet)
2. Stores and tracks attestation UIDs for each multisig address
3. Queries and categorizes attestations by schema type (activity, votes, opportunities, no-opportunities)
4. Returns the aggregated statistics in the required format

The solution involves creating an EASQuorumTracker contract that maintains mappings of attestations per multisig, validates them against registered schemas, and provides view functions to retrieve voting statistics.

## Detailed Findings

### IQuorumTracker Interface Requirements
The QuorumStakingTokenActivityChecker contract at line 26 requires:
- Interface: `IQuorumTracker`
- Method: `getVotingStats(address multisig) external view returns (uint256[] memory)`
- Return Array Structure (4 elements):
  1. **Multisig activity** - General activity count
  2. **Casted votes** - Number of actual votes submitted
  3. **Considered voting opportunities** - Total opportunities evaluated
  4. **No voting opportunities available** - Cases where no voting was possible

### Ethereum Attestation Service (EAS) Integration

#### Core EAS Contracts
- **Mainnet EAS Contract**: `0xA1207F3BBa224E2c9c3c6D5aF63D0eb1582Ce587`
- **Mainnet SchemaRegistry**: `0xA7b39296258348C78294F95B872b282326A97BDF`
- **Layer 2 Predeploy (Base/OP Stack)**: `0x4200000000000000000000000000000000000021`

#### Key EAS Interfaces
```solidity
interface IEAS {
    function getAttestation(bytes32 uid) external view returns (Attestation memory);
    function isAttestationValid(bytes32 uid) external view returns (bool);
    function attest(AttestationRequest calldata request) external payable returns (bytes32);
}

struct Attestation {
    bytes32 uid;
    bytes32 schema;
    address recipient;
    address attester;
    uint64 time;
    uint64 expirationTime;
    bool revocable;
    bytes data;
}
```

### Complete EASQuorumTracker Implementation

The complete implementation includes:

1. **Constructor Parameters**:
   - EAS contract address
   - Four schema UIDs for different attestation types
   - Validation of all parameters

2. **Storage Architecture**:
   - `mapping(address => bytes32[])` for multisig attestations
   - `mapping(bytes32 => bool)` for processed attestations
   - `mapping(address => uint256)` for tracking last update blocks

3. **Registration Methods**:
   - `registerAttestation()` - Register individual attestations
   - `batchRegisterAttestations()` - Batch registration for gas efficiency

4. **Query Methods**:
   - `getVotingStats()` - Main interface implementation
   - `getVotingStatsInTimeRange()` - Time-filtered statistics
   - `getAttestationCount()` - Total attestations per multisig
   - `getAllAttestationUIDs()` - Retrieve all attestation IDs

5. **Gas Optimization Strategies**:
   - Batch processing up to 50 attestations
   - Early exit for invalid attestations
   - View functions for zero-gas queries
   - Schema validation to skip irrelevant attestations

## Code References

### Existing Codebase Integration Points
- `/Users/max/code/quorum-ai/backend/services/safe_service.py:436-563` - Current EAS attestation implementation
- `/Users/max/code/quorum-ai/backend/models.py:982-1002` - EASAttestationData model
- `/Users/max/code/quorum-ai/backend/abi/eas.json` - EAS contract ABI
- `/Users/max/code/quorum-ai/backend/utils/abi_loader.py` - ABI loading utilities
- `/Users/max/code/quorum-ai/backend/services/agent_run_service.py:1244-1369` - Statistical aggregation patterns

### Schema Definitions for Attestation Types

1. **Activity Schema** (New):
   ```
   address agent, string action, uint256 timestamp, string runId, string metadata
   ```

2. **Voting Schema** (Existing from `/Users/max/code/quorum-ai/README.md:241`):
   ```
   address agent, string spaceId, string proposalId, uint8 voteChoice, string snapshotSig, uint256 timestamp, string runId, uint8 confidence
   ```

3. **Opportunity Schema** (New):
   ```
   address agent, string spaceId, string proposalId, uint8 opportunityType, uint256 timestamp, string runId, string reason
   ```

4. **No-Opportunity Schema** (New):
   ```
   address agent, string spaceId, uint256 timestamp, string runId, string reason
   ```

## Architecture Insights

### Current Architecture Patterns
1. **No Native Solidity Contracts**: The quorum-ai codebase uses Python services with Web3.py rather than deploying custom contracts
2. **ABI-Based Integration**: All contract interactions use stored ABI definitions in `/backend/abi/`
3. **Safe Multisig Pattern**: Primary on-chain interactions route through Safe multisig wallets
4. **EAS Integration Exists**: Backend already creates EAS attestations for Snapshot votes
5. **Statistical Aggregation**: Agent run service demonstrates data aggregation patterns applicable to QuorumTracker

### Deployment Options

#### Option 1: Deploy EASQuorumTracker Contract
Deploy the provided Solidity contract with:
- Constructor parameters for EAS address and schema UIDs
- Registration of attestations after creation
- Direct integration with QuorumStakingTokenActivityChecker

#### Option 2: Python Service Integration (Current Pattern)
Extend existing Python services to:
- Query EAS attestations using Web3.py
- Aggregate statistics off-chain
- Provide data through an oracle or keeper mechanism

## Historical Context (from thoughts/)
The codebase has evolved from using Tally to Snapshot for DAO data (BAC-157 migration). EAS integration was added to create permanent on-chain records of votes, providing an immutable audit trail. The current implementation focuses on creating attestations but doesn't yet aggregate them for external consumption.

## Related Research
- [EAS Documentation](https://docs.attest.org/)
- [EAS Contracts GitHub](https://github.com/ethereum-attestation-service/eas-contracts)
- [Autonolas Staking Programs](https://github.com/valory-xyz/autonolas-staking-programmes)

## Implementation Recommendations

### For Solidity Contract Deployment:
1. Deploy EASQuorumTracker contract with appropriate schema UIDs
2. Register attestations immediately after creation in safe_service.py
3. Verify contract on Etherscan/BaseScan for transparency
4. Add monitoring for attestation registration events

### For Python Service Extension:
1. Add QuorumTracker methods to safe_service.py
2. Create periodic aggregation tasks for statistics
3. Implement caching for efficient queries
4. Add API endpoints for statistics retrieval

### Testing Strategy:
1. Unit tests for attestation registration logic
2. Integration tests with mock EAS contract
3. Gas optimization testing for batch operations
4. Time-range query performance testing

## Open Questions
1. Should attestation registration be automatic or require explicit calls?
2. What retention period should be used for historical attestations?
3. Should the contract support upgradability patterns?
4. How should revoked attestations affect historical statistics?
5. What gas limits are acceptable for batch registration operations?