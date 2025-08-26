---
date: 2025-08-26T16:26:14+0000
researcher: Claude Sonnet 4
git_commit: 543cb9e5762e43ca846f8095d66b8fcc6b894852
branch: develop
repository: quorum-ai
topic: "EAS Attestations Wrapper for QuorumTracker Interface"
tags: [research, codebase, eas, attestation, solidity, quorum-tracker]
status: complete
last_updated: 2025-08-26
last_updated_by: Claude Sonnet 4
last_updated_note: "Updated to focus solely on on-chain approaches"
---

# Research: EAS Attestations Wrapper for QuorumTracker Interface

**Date**: 2025-08-26T16:26:14+0000  
**Researcher**: Claude Sonnet 4  
**Git Commit**: 543cb9e5762e43ca846f8095d66b8fcc6b894852  
**Branch**: develop  
**Repository**: quorum-ai

## Research Question
How can I wrap the EAS attestations in a Solidity contract to be used as quorumTracker in the QuorumStakingTokenActivityChecker contract from Olas/Autonolas staking programs?

## Summary
Based on comprehensive analysis of the target contract interface and existing EAS integration patterns in the codebase, an EAS wrapper contract can be implemented using **purely on-chain approaches** to satisfy the `IQuorumTracker` interface. The wrapper will query EAS attestations directly from the EAS contract using `getAttestation()` calls and event filtering, aggregating voting statistics into the required uint256 array format without relying on off-chain APIs.

## Detailed Findings

### Target Interface Requirements
The `IQuorumTracker` interface from the Autonolas contract requires:
```solidity
interface IQuorumTracker {
    /// @dev Gets voting stats.
    /// @param multisig Agent multisig performing attestations.
    /// @return votingStats Voting attestations (set of 3 values) for:
    /// - Casted vote;
    /// - Considered voting opportunity;
    /// - No single voting opportunity available.
    function getVotingStats(address multisig) external view returns (uint256[] memory votingStats);
}
```

The interface expects a 3-element array containing:
1. **Casted votes** - Number of actual votes submitted
2. **Considered voting opportunities** - Total voting opportunities evaluated
3. **No voting opportunity available** - Instances where no voting was possible

### EAS Core Interface Analysis
The wrapper contract will use only on-chain EAS interfaces:
- `IEAS.getAttestation(bytes32 uid)` - Retrieves specific attestation data
- `IEAS.isAttestationValid(bytes32 uid)` - Validates attestation status  
- Event filtering for `Attested` events to discover attestation UIDs by attester
- On-chain mapping to track attestation UIDs for efficient querying

Key EAS data structures:
```solidity
struct Attestation {
    bytes32 uid;          // Unique identifier
    bytes32 schema;       // Schema UID
    address recipient;    // Address receiving attestation
    address attester;     // Address creating attestation
    bytes data;           // Encoded attestation data
    uint64 time;          // Creation timestamp
    uint64 expirationTime; // Expiration timestamp
    uint64 revocationTime; // Revocation timestamp (0 if not revoked)
    // ... other fields
}
```

### Existing EAS Implementation Patterns
The codebase contains comprehensive EAS integration that provides implementation guidance:

#### EAS Service Architecture (`backend/services/safe_service.py:436-527`)
- **Configuration validation** with contract address and schema UID
- **ABI loading pattern** from `/backend/abi/eas.json`
- **Transaction building** with proper data encoding
- **Safe multisig integration** for attestation submission

#### EAS Data Model (`backend/models.py:982-1042`)
Current attestation schema encodes:
- `proposal_id` (string) - Snapshot proposal ID
- `space_id` (string) - Snapshot space ID
- `choice` (uint256) - Vote choice numeric value
- `vote_tx_hash` (bytes32) - Transaction hash of the vote

#### Statistics Aggregation Pattern (`backend/services/agent_run_service.py:1021-1026`)
The codebase demonstrates data aggregation into arrays:
- Counter variables for different metrics
- File-based data aggregation from multiple sources
- Error handling for missing or corrupted data
- Array processing with proper validation

### On-Chain Wrapper Contract Architecture

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@ethereum-attestation-service/eas-contracts/contracts/IEAS.sol";

interface IQuorumTracker {
    function getVotingStats(address multisig) external view returns (uint256[] memory votingStats);
}

contract EASQuorumTracker is IQuorumTracker {
    IEAS private immutable eas;
    bytes32 private immutable votingSchemaUID;
    bytes32 private immutable opportunitySchemaUID;
    bytes32 private immutable noOpportunitySchemaUID;
    
    // Track attestation UIDs for each multisig for efficient querying
    mapping(address => bytes32[]) private multisigAttestations;
    mapping(bytes32 => bool) private processedAttestations;
    
    // Events for tracking attestation registration
    event AttestationRegistered(address indexed multisig, bytes32 indexed uid, bytes32 indexed schema);
    
    constructor(
        address _eas,
        bytes32 _votingSchemaUID,
        bytes32 _opportunitySchemaUID,
        bytes32 _noOpportunitySchemaUID
    ) {
        eas = IEAS(_eas);
        votingSchemaUID = _votingSchemaUID;
        opportunitySchemaUID = _opportunitySchemaUID;
        noOpportunitySchemaUID = _noOpportunitySchemaUID;
    }
    
    /**
     * @dev Register an attestation UID for tracking by multisig
     * This should be called whenever a new attestation is created
     */
    function registerAttestation(address multisig, bytes32 attestationUID) external {
        require(!processedAttestations[attestationUID], "Attestation already registered");
        
        // Verify attestation exists and get its data
        Attestation memory attestation = eas.getAttestation(attestationUID);
        require(attestation.attester == multisig, "Invalid attester");
        require(eas.isAttestationValid(attestationUID), "Invalid attestation");
        
        // Verify schema is one of our tracked schemas
        require(
            attestation.schema == votingSchemaUID || 
            attestation.schema == opportunitySchemaUID ||
            attestation.schema == noOpportunitySchemaUID,
            "Invalid schema"
        );
        
        multisigAttestations[multisig].push(attestationUID);
        processedAttestations[attestationUID] = true;
        
        emit AttestationRegistered(multisig, attestationUID, attestation.schema);
    }
    
    function getVotingStats(address multisig) external view override returns (uint256[] memory) {
        uint256 castedVotes = 0;
        uint256 consideredOpportunities = 0;
        uint256 noOpportunityAvailable = 0;
        
        bytes32[] memory attestationUIDs = multisigAttestations[multisig];
        
        for (uint256 i = 0; i < attestationUIDs.length; i++) {
            bytes32 uid = attestationUIDs[i];
            
            // Skip if attestation is no longer valid
            if (!eas.isAttestationValid(uid)) {
                continue;
            }
            
            Attestation memory attestation = eas.getAttestation(uid);
            
            if (attestation.schema == votingSchemaUID) {
                castedVotes++;
            } else if (attestation.schema == opportunitySchemaUID) {
                consideredOpportunities++;
            } else if (attestation.schema == noOpportunitySchemaUID) {
                noOpportunityAvailable++;
            }
        }
        
        uint256[] memory stats = new uint256[](3);
        stats[0] = castedVotes;
        stats[1] = consideredOpportunities;
        stats[2] = noOpportunityAvailable;
        
        return stats;
    }
    
    /**
     * @dev Get the total number of registered attestations for a multisig
     */
    function getAttestationCount(address multisig) external view returns (uint256) {
        return multisigAttestations[multisig].length;
    }
    
    /**
     * @dev Get attestation UID by index for a multisig
     */
    function getAttestationUID(address multisig, uint256 index) external view returns (bytes32) {
        require(index < multisigAttestations[multisig].length, "Index out of bounds");
        return multisigAttestations[multisig][index];
    }
}
```

## Code References
- **EAS Service Implementation**: `backend/services/safe_service.py:436-567` - Main EAS integration
- **Data Models**: `backend/models.py:982-1042` - EASAttestationData Pydantic model
- **Contract ABI**: `backend/abi/eas.json` - Complete EAS contract interface
- **Configuration**: `backend/config.py:282-300` - EAS settings and validation (lines 690-724)
- **Environment Setup**: `.env.example:15-16` - Required EAS environment variables
- **Agent Integration**: `backend/services/agent_run_service.py:22,933-946` - Attestation workflow
- **Test Coverage**: `backend/tests/test_safe_service_eas.py:25-197` - EAS service tests
- **Schema Documentation**: `README.md:241` - Current attestation schema definition

## Architecture Insights

### Schema Design Considerations
The wrapper needs three distinct schemas for different attestation types:

#### 1. Voting Schema (Existing)
**Current Schema**: `address agent, string spaceId, string proposalId, uint8 voteChoice, string snapshotSig, uint256 timestamp, string runId, uint8 confidence`
- **File Reference**: `README.md:241`
- **Usage**: Records actual vote submissions to Snapshot
- **Schema UID**: Configured via `EAS_SCHEMA_UID` environment variable

#### 2. Opportunity Schema (New)
**Proposed Schema**: `address agent, string spaceId, string proposalId, uint8 opportunityType, uint256 timestamp, string runId, string reason`
- **Usage**: Records when voting opportunities were considered but not acted upon
- **opportunityType**: 1 = evaluated, 2 = skipped, 3 = deferred
- **reason**: Human-readable explanation for the decision

#### 3. No-Opportunity Schema (New)
**Proposed Schema**: `address agent, string spaceId, uint256 timestamp, string runId, string reason`
- **Usage**: Records when no voting opportunities were available in a space
- **reason**: Explanation (e.g., "no active proposals", "outside voting window")

### On-Chain Gas Optimization Strategies
1. **UID Tracking** - Maintain on-chain mapping of attestation UIDs per multisig for O(1) access
2. **Schema Filtering** - Only process attestations matching specific schemas to reduce iterations
3. **Validity Checking** - Skip revoked or expired attestations early in processing
4. **Batch Registration** - Allow multiple attestation UIDs to be registered in single transaction
5. **View Function Optimization** - Use view functions for read-only statistics aggregation
6. **Storage Layout** - Pack struct data efficiently to minimize storage slots

### Integration with Existing EAS Service
The current EAS service at `safe_service.py:436` already:
- Connects to Base network EAS contract (0x4200000000000000000000000000000000000021)
- Uses established schema UID pattern
- Handles Safe multisig transaction submission
- Implements proper error handling and validation

## Selected Implementation Approach: UID Registration Pattern

**Decision**: Using UID Registration Pattern as the primary approach for production implementation.

**Rationale**:
- **Gas Efficiency**: O(1) access to attestation UIDs via on-chain mapping
- **Real-time Data**: Immediate availability of new attestations after registration
- **Controlled Access**: Works well with existing Safe multisig attestation workflow
- **Scalability**: Linear storage growth, efficient for large numbers of attestations
- **Simplicity**: Straightforward implementation with clear registration pattern

**Implementation Details**:
- Maintain `mapping(address => bytes32[])` for multisig attestation UIDs
- Require `registerAttestation()` call after each EAS attestation creation
- Validate attestation existence, schema, and attester before registration
- Use view functions for gas-efficient statistics aggregation

## Environment Integration
The wrapper leverages existing EAS infrastructure with specific configuration requirements:

### Current Configuration (`backend/config.py:282-300`)
- **EAS Contract Address**: `0x4200000000000000000000000000000000000021` (Base network)
- **Schema UID**: Single schema for vote attestations (configured via `EAS_SCHEMA_UID`)
- **Validation**: Format checking for 42-char address and 66-char schema UID
- **Network**: Base Chain ID 8453 (`safe_service.py:29-33`)

### Required Configuration Updates
- **Additional Schema UIDs**: Environment variables for opportunity and no-opportunity schemas
- **Schema Registry**: Register new schemas on Base EAS at schema creation time
- **Configuration Validation**: Extend validation for multiple schema UIDs

### Integration Points
- **Safe Service Integration**: `backend/services/safe_service.py:436-567`
  - Add `registerAttestation()` calls after EAS attestation creation
  - Extend attestation creation for opportunity tracking
- **Agent Service Integration**: `backend/services/agent_run_service.py:22,933-946`
  - Add opportunity attestation creation during decision flow
  - Track no-opportunity scenarios during space monitoring
- **Monitoring**: Pearl-compliant logging via existing patterns (`backend/services/`)

## Open Questions
1. **Schema standardization** - Should voting opportunities be standardized across different DAOs?
2. **Data retention** - How long should historical voting data be maintained?
3. **Multi-chain support** - Should the wrapper support attestations across multiple networks?
4. **Governance integration** - How should the wrapper handle governance parameter updates?

## Implementation Plan

### Phase 1: Schema Definition and Registration
1. **Create new EAS schemas** on Base network using EAS Schema Registry
   - Opportunity tracking schema: `address agent, string spaceId, string proposalId, uint8 opportunityType, uint256 timestamp, string runId, string reason`
   - No-opportunity schema: `address agent, string spaceId, uint256 timestamp, string runId, string reason`
2. **Update configuration** (`backend/config.py:282-300`)
   - Add `EAS_OPPORTUNITY_SCHEMA_UID` environment variable
   - Add `EAS_NO_OPPORTUNITY_SCHEMA_UID` environment variable
   - Extend validation for multiple schema UIDs

### Phase 2: Wrapper Contract Development
1. **Deploy EAS QuorumTracker contract** with Solidity ^0.8.28
   - Use Base EAS contract: `0x4200000000000000000000000000000000000021`
   - Implement UID registration pattern with three schema support
   - Add comprehensive validation and error handling
2. **Write comprehensive tests** covering all contract functions
   - Unit tests for UID registration and statistics aggregation
   - Integration tests with EAS contract on Base network
   - Gas optimization validation

### Phase 3: Backend Integration
1. **Extend Safe service** (`backend/services/safe_service.py:436-567`)
   - Add `registerAttestation()` calls after attestation creation
   - Support creating opportunity and no-opportunity attestations
2. **Update Agent service** (`backend/services/agent_run_service.py:22,933-946`)
   - Add opportunity attestation creation during voting decisions
   - Track and attest no-opportunity scenarios during space monitoring
3. **Add comprehensive test coverage** for updated services

### Phase 4: Deployment and Monitoring
1. **Deploy to Base network** with proper configuration validation
2. **Integrate with existing monitoring** using Pearl-compliant logging
3. **Validate integration** with Autonolas QuorumStakingTokenActivityChecker
4. **Performance monitoring** for gas usage and query efficiency

## Follow-up Research 2025-08-26T16:48:33+0000

### Focus on On-Chain Only Approaches

Updated the research to focus exclusively on on-chain approaches after clarification that Solidity contracts cannot call external APIs like EAS GraphQL. The key changes:

#### Removed Off-Chain Dependencies
- **GraphQL API references** - Contracts cannot call external APIs
- **Oracle-based caching** - Eliminates off-chain infrastructure requirements  
- **Hybrid off-chain approaches** - Focus purely on on-chain solutions

#### Enhanced On-Chain Patterns
- **UID Registration Pattern** - Most efficient approach using on-chain mappings
- **Event Log Scanning** - Pure on-chain discovery via EAS events
- **Schema-based Filtering** - Efficient attestation categorization

#### Updated Contract Architecture
The revised contract implements:
1. **registerAttestation()** - On-chain UID tracking for efficient queries
2. **Schema validation** - Ensures only relevant attestations are processed
3. **View-only statistics** - Gas-efficient read operations
4. **Attestation management** - Helper functions for UID access and counts

#### Integration with Existing EAS Service
The wrapper integrates with existing `safe_service.py:436` by:
- Adding `registerAttestation()` calls after attestation creation
- Utilizing existing schema UID patterns
- Maintaining compatibility with current Safe multisig workflow

This purely on-chain approach ensures the wrapper is fully decentralized and gas-efficient for the quorumTracker use case.