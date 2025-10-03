# Staking System Data Flow and Contract Interactions

## Overview
This document clarifies how data flows between the various staking contracts and how they interact to validate agent activity and distribute rewards.

## Contract Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                         User/Agent                           │
└─────────────┬───────────────────────────────┬───────────────┘
              │                               │
              │ 1. Stake/Unstake             │ 5. Make Attestations
              ↓                               ↓
┌─────────────────────────┐     ┌────────────────────────────┐
│     StakingToken        │     │   AttestationTracker       │
│  0xEB5638eefE289691...  │     │  0x9BC8c713a159a028a...    │
│                         │     │                            │
│ - Holds staked tokens   │     │ - Counts attestations      │
│ - Manages rewards       │     │ - Stores active status     │
│ - Tracks service state  │     │ - Forwards to EAS          │
└──────────┬──────────────┘     └────────────┬───────────────┘
           │                                  │
           │ 2. Check Activity                │ 6. Forward attestation
           ↓                                  ↓
┌──────────────────────────────────┐   ┌────────────────────┐
│ QuorumStakingTokenActivityChecker│   │        EAS         │
│   0x747262cC12524C571e08f...     │   │ 0xF095fE4b2395... │
│                                  │   │                    │
│ - Validates activity ratio       │   │ - Records on-chain │
│ - Checks liveness threshold      │   │   attestations     │
└──────────┬───────────────────────┘   └────────────────────┘
           │
           │ 3. Query attestation count
           ↓
┌──────────────────────────────────┐
│    AttestationTracker (again)    │
│    Acting as QuorumTracker       │
│                                  │
│ - Returns voting stats           │
│ - Provides attestation count     │
└──────────────────────────────────┘
```

## Detailed Data Flow

### Phase 1: Setup and Staking

1. **StakingFactory deploys StakingToken**
   ```solidity
   StakingFactory (0x1cEe30D08943EB58EFF84DD1AB44a6ee6FEff63a)
     → create2()
     → Returns: New StakingToken address
     → Configuration: Links to ActivityChecker (0x747262...)
   ```

2. **User stakes their service**
   ```solidity
   StakingToken.stake(serviceId)
     → Validates service registration
     → Transfers OLAS tokens from user
     → Records: {
         multisig: 0xSafeAddress,
         owner: msg.sender,
         tsStart: block.timestamp,
         state: "Staked"
       }
   ```

### Phase 2: Activity Generation

3. **Agent makes attestations**
   ```solidity
   AttestationTracker (0x9BC8c713...).attestByDelegation(request)
     → Increments: mapMultisigAttestations[msg.sender]++
     → Forwards to: EAS.attest(request)
     → Returns: attestationUID
     → Emits: AttestationMade(msg.sender, attestationUID)
   ```

4. **Data storage in AttestationTracker**
   ```solidity
   // Storage layout (single uint256 per multisig)
   mapMultisigAttestations[multisig] = 
     [Bit 255: Active Status | Bits 0-254: Attestation Count]
   
   // Example: Active multisig with 10 attestations
   0x800000000000000000000000000000000000000000000000000000000000000A
   ```

### Phase 3: Activity Validation

5. **Checkpoint triggers activity check**
   ```solidity
   StakingToken.checkpoint()
     → Calls: ActivityChecker.getMultisigNonces(multisig)
     → ActivityChecker queries: AttestationTracker.getVotingStats(multisig)
   ```

6. **ActivityChecker retrieves data**
   ```solidity
   QuorumStakingTokenActivityChecker (0x747262...).getMultisigNonces(multisig)
     → Queries: quorumTracker.getVotingStats(multisig)
     → quorumTracker = AttestationTracker (0x9BC8c713...)
     → Returns: [
         nonce,           // Multisig transaction count
         votesCount,      // Attestations made
         votingOpps,      // Opportunities considered
         noOppsCount      // No-opportunity instances
       ]
   ```

7. **Activity ratio calculation**
   ```solidity
   ActivityChecker.isRatioPass(currentNonces, lastNonces, timeElapsed)
     → Calculate: ratio = (currentNonces[1] - lastNonces[1]) / timeElapsed
     → Compare: ratio >= livenessRatio (11574074074074)
     → Returns: true if active, false if inactive
   ```

### Phase 4: Reward Distribution

8. **Rewards calculated based on activity**
   ```solidity
   if (activityChecker.isRatioPass(...)) {
     reward = (stake * APY * time) / (365 days * 100)
     service.reward += reward
   } else {
     // No rewards for inactive period
     service.inactive = true
   }
   ```

9. **User unstakes and claims**
   ```solidity
   StakingToken.unstake(serviceId)
     → Final activity check
     → Calculate total rewards
     → Transfer: stake + rewards → user
     → Reset service state
   ```

## Key Interactions Explained

### Why AttestationTracker serves dual purpose:

The `AttestationTracker` contract (0x9BC8c713...) implements two interfaces:

1. **As AttestationTracker**: 
   - Primary function: Count attestations
   - Called by: Agents making attestations
   - Stores: Attestation count per multisig

2. **As QuorumTracker**:
   - Secondary function: Provide voting statistics
   - Called by: ActivityChecker
   - Returns: Formatted voting stats for activity validation

### Data flow when checking activity:

```
StakingToken → "Is service active?" 
    ↓
ActivityChecker → "Get voting stats"
    ↓
AttestationTracker → "Here's the data"
    ↓
ActivityChecker → "Calculate ratio"
    ↓
StakingToken → "Apply rewards or penalties"
```

## Concrete Example

Let's trace a complete flow with actual values:

1. **Service stakes on Day 1**
   - StakingToken records: `tsStart = 1700000000`
   - Initial attestation count: `0`

2. **Agent makes 5 attestations over 5 days**
   - AttestationTracker increments counter 5 times
   - Storage: `0x8000000000000000000000000000000000000000000000000000000000000005`

3. **Checkpoint called on Day 6**
   ```solidity
   // ActivityChecker retrieves:
   currentNonces = [10, 5, 5, 0]  // 10 txs, 5 attestations
   lastNonces = [5, 0, 0, 0]      // Previous checkpoint
   timeElapsed = 432000            // 5 days in seconds
   
   // Calculate ratio:
   ratio = (5 - 0) * 1e18 / 432000 = 11574074074 
   
   // Compare to threshold:
   11574074074 >= 11574074074074 ? NO
   // Need ~1000x more activity!
   ```

4. **Result**: Service marked inactive, no rewards

## Critical Understanding Points

1. **StakingToken IS DEPLOYED** at `0xEB5638eefE289691EcE01943f768EDBF96258a80`
2. **System is FULLY ACTIVE** - Services can stake, earn rewards, and be validated
3. **AttestationTracker is recording** - Attestations count toward activity requirements
4. **ActivityChecker is configured** - Requires ~1 action per day to maintain rewards
5. **Up to 2 services can stake** - Limited slots available (maxNumServices = 2)
6. **10 OLAS minimum deposit** - Services need at least 10 OLAS tokens to stake

## Testing the Flow Locally

```bash
# 1. Check StakingToken configuration
cast call 0xEB5638eefE289691EcE01943f768EDBF96258a80 \
  "activityChecker()" \
  --rpc-url http://localhost:8545
# Returns: 0x747262cC12524C571e08faCb6E6994EF2E3B97ab

# 2. Check if any services are staked
cast call 0xEB5638eefE289691EcE01943f768EDBF96258a80 \
  "getNumServices()" \
  --rpc-url http://localhost:8545

# 3. Check rewards configuration
cast call 0xEB5638eefE289691EcE01943f768EDBF96258a80 \
  "rewardsPerSecond()" \
  --rpc-url http://localhost:8545
# Returns: 824652777778 (wei/second)

# 4. Check current attestation count for a multisig
cast call 0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC \
  "getAttestationCount(address)" "YOUR_MULTISIG_ADDRESS" \
  --rpc-url http://localhost:8545

# 5. Check if activity ratio passes
cast call 0x747262cC12524C571e08faCb6E6994EF2E3B97ab \
  "isRatioPass(uint256[],uint256[],uint256)" \
  "[10,1,1,0]" "[5,0,0,0]" "86400" \
  --rpc-url http://localhost:8545

# 6. Get liveness threshold
cast call 0x747262cC12524C571e08faCb6E6994EF2E3B97ab \
  "livenessRatio()(uint256)" \
  --rpc-url http://localhost:8545
# Returns: 11574074074074

# 7. Check minimum staking deposit
cast call 0xEB5638eefE289691EcE01943f768EDBF96258a80 \
  "minStakingDeposit()" \
  --rpc-url http://localhost:8545
# Returns: 10000000000000000000 (10 OLAS)
```

## Summary

The staking system is a carefully orchestrated interaction between:
- **StakingToken**: Manages stakes and rewards (not yet deployed)
- **ActivityChecker**: Validates activity meets thresholds
- **AttestationTracker**: Records attestations and provides stats
- **EAS**: Stores attestations permanently on-chain

Data flows from user actions → attestation recording → activity validation → reward distribution, with each contract playing a specific role in the verification chain.