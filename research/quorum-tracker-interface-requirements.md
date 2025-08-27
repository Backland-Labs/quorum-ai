# IQuorumTracker Interface Requirements

Based on analysis of `QuorumStakingTokenActivityChecker.sol` from the Autonolas staking programs repository.

## 1. Required Interface Definition

Your EAS wrapper contract must implement the following interface:

```solidity
interface IQuorumTracker {
    /// @dev Gets voting stats.
    /// @param multisig Agent multisig performing attestations.
    /// @return votingStats Voting attestations (set of 3 values) for:
    ///         - Casted vote;
    ///         - Considered voting opportunity;
    ///         - No single voting opportunity available.
    function getVotingStats(address multisig) external view returns (uint256[] memory votingStats);
}
```

## 2. Return Structure Requirements

The `getVotingStats` function MUST return a `uint256[]` array with **exactly 3 elements**:

1. **votingStats[0]** - Count of attestations for "Casted vote"
2. **votingStats[1]** - Count of attestations for "Considered voting opportunity" 
3. **votingStats[2]** - Count of attestations for "No single voting opportunity available"

## 3. How QuorumStakingTokenActivityChecker Uses the Interface

### Usage in `getMultisigNonces`:
```solidity
// Get voting stats from the quorumTracker
uint256[] memory votingStats = IQuorumTracker(quorumTracker).getVotingStats(multisig);

nonces = new uint256[](4);
nonces[0] = IMultisig(multisig).nonce();  // Multisig activity
nonces[1] = votingStats[0];               // Casted vote attestations
nonces[2] = votingStats[1];               // Considered opportunity attestations  
nonces[3] = votingStats[2];               // No opportunity attestations
```

### Usage in `isRatioPass` (Reward Logic):
The activity checker uses these stats to determine if staking rewards should be given:

1. **Primary Path**: If `votingStats[0]` (casted votes) increased, rewards are achieved with at least 1x attestation meeting the `livenessRatio`.

2. **Alternative Path**: If no votes were cast, rewards can still be achieved with at least 2x attestations for either:
   - Voting opportunity considered but not voted (`votingStats[1]`)
   - No voting opportunity available (`votingStats[2]`)
   
   Note: The alternative path requires `2 * livenessRatio` to qualify.

## 4. Implementation Constraints

1. **Function Visibility**: Must be `external view`
2. **Parameter**: Takes a single `address` parameter (the multisig address)
3. **Return Type**: Must return `uint256[] memory` with exactly 3 elements
4. **Gas Efficiency**: Should be optimized as it's called frequently for activity checks
5. **Data Accuracy**: Counts must accurately reflect attestations from EAS

## 5. Key Considerations for EAS Wrapper Implementation

1. **Attestation Schema**: Your EAS attestations must capture the three voting states:
   - Actual votes cast
   - Opportunities considered but not voted
   - No opportunities available

2. **Multisig Tracking**: Must be able to filter attestations by the multisig address parameter

3. **Count Accumulation**: Must return cumulative counts (not reset) as the activity checker compares current vs previous values

4. **Immutability**: Once an attestation is made, its count should not decrease (only increase or stay the same)

## 6. Contract Deployment Requirements

When the `QuorumStakingTokenActivityChecker` is deployed, it expects:
- Your EAS wrapper contract address as the `_quorumTracker` parameter
- A `_livenessRatio` value (in 1e18 format) for activity threshold checks

## Example Implementation Pattern

```solidity
contract EASQuorumTracker is IQuorumTracker {
    // EAS contract reference
    IEAS public immutable eas;
    bytes32 public immutable schemaUID;
    
    function getVotingStats(address multisig) 
        external 
        view 
        override 
        returns (uint256[] memory votingStats) 
    {
        votingStats = new uint256[](3);
        
        // Query EAS attestations for this multisig
        // Parse attestation data to categorize into the 3 types
        // Accumulate counts for each category
        
        votingStats[0] = castedVoteCount;
        votingStats[1] = consideredOpportunityCount;
        votingStats[2] = noOpportunityCount;
        
        return votingStats;
    }
}
```