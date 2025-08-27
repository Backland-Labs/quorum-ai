# AttestationTracker Contract

A minimal, clean implementation of the DualStakingToken attestation pattern for tracking EAS (Ethereum Attestation Service) attestations made by multisig addresses.

## Overview

The `AttestationTracker` contract serves as a wrapper around EAS that:
- Tracks which multisig addresses make attestations
- Maintains an active/inactive status for each multisig
- Uses efficient bit manipulation for storage optimization
- Forwards all attestations to EAS while maintaining local tracking

## Key Features

### 1. Attestation Tracking
- Increments a counter each time a multisig makes an attestation
- Stores attestation count in lower 255 bits of a uint256
- Emits events for off-chain tracking

### 2. Active Status Management
- Owner can mark multisigs as active/inactive
- Active status stored in MSB (most significant bit)
- Status changes don't affect attestation counts

### 3. Bit Manipulation Pattern
Following the DualStakingToken pattern:
- **MSB (bit 255)**: Active status (1 = active, 0 = inactive)
- **Lower 255 bits**: Attestation counter
- Single storage slot per multisig for gas efficiency

### 4. EAS Integration
- Acts as a transparent wrapper around EAS
- Forwards all attestation requests with ETH value
- Returns the actual attestation UID from EAS

## Contract Interface

### Core Functions

```solidity
function attestByDelegation(IEAS.DelegatedAttestationRequest calldata delegatedRequest) 
    external 
    payable 
    returns (bytes32 attestationUID);
```
- **Purpose**: Main wrapper function for EAS attestations
- **Access**: Public (any address can call)
- **Behavior**: Increments caller's attestation count and forwards to EAS

```solidity
function setMultisigActiveStatus(address multisig, bool active) external onlyOwner;
```
- **Purpose**: Set active/inactive status for a multisig
- **Access**: Owner only
- **Behavior**: Updates MSB while preserving attestation count

### View Functions

```solidity
function getNumAttestations(address multisig) external view returns (uint256);
```
- Returns the attestation count for a multisig (excludes MSB)

```solidity
function isMultisigActive(address multisig) external view returns (bool);
```
- Returns whether a multisig is marked as active

```solidity
function getMultisigInfo(address multisig) 
    external 
    view 
    returns (uint256 numAttestations, bool isActive);
```
- Gas-efficient function returning both values in one call

## Deployment

### Environment Variables Required
```bash
ATTESTATION_TRACKER_OWNER=0x...     # Contract owner address
EAS_CONTRACT_ADDRESS=0x...          # EAS contract address
PRIVATE_KEY=0x...                   # Deployer private key
```

### Deploy Command
```bash
forge script script/Deploy.s.sol --rpc-url <network> --broadcast --verify -vvv
```

## Testing

### Run All Tests
```bash
forge test --match-contract AttestationTrackerTest -vvv
```

### Run Specific Test Categories
```bash
# Basic functionality
forge test --match-test test_ -vv

# Fuzz tests
forge test --match-test testFuzz -vv --fuzz-runs 1000

# Gas optimization tests
forge test --match-test test_Gas -vv --gas-report
```

### Test Coverage
The test suite includes:
- ✅ Constructor validation
- ✅ Active status management
- ✅ Attestation wrapper functionality
- ✅ Bit manipulation correctness
- ✅ Multi-multisig independence
- ✅ Event emission
- ✅ Gas efficiency
- ✅ Edge cases (overflow, maximum values)
- ✅ Fuzz testing
- ✅ Access control

## Bit Manipulation Details

### Storage Layout
```
uint256 mapMultisigAttestations[address]
├── Bit 255 (MSB): Active status
└── Bits 0-254: Attestation counter (max: 2^255 - 1)
```

### Operations
```solidity
// Set active (preserve count)
mapping[addr] |= 1 << 255;

// Set inactive (preserve count)
mapping[addr] &= ((1 << 255) - 1);

// Increment attestation count (preserve status)
mapping[addr]++;

// Extract attestation count
count = mapping[addr] & ((1 << 255) - 1);

// Extract active status
active = (mapping[addr] >> 255) == 1;
```

## Gas Optimization

- **Single SLOAD/SSTORE**: Both values stored in one slot
- **Batch View Function**: `getMultisigInfo()` reads both values efficiently
- **Minimal Storage**: Only necessary state is maintained
- **No Dynamic Arrays**: Uses mappings for O(1) access

## Security Considerations

- **Owner Access Control**: Only owner can set active status
- **Input Validation**: Constructor validates EAS address
- **Reentrancy**: External calls to EAS are at the end of functions
- **Overflow Protection**: Solidity 0.8.24 has built-in overflow protection
- **Address Validation**: Zero address checks where appropriate

## Migration from Previous Implementation

This contract replaces `QuorumTrackerWithAttestations` with a cleaner implementation that:

### Removed Features
- ❌ Voting statistics tracking (`getVotingStats`, `register`)
- ❌ Legacy interface compatibility (`IQuorumTracker`)
- ❌ Complex multi-return functions

### Retained Core Features
- ✅ Attestation counter (`mapMultisigAttestations`)
- ✅ EAS wrapper (`attestByDelegation`)
- ✅ Active status management
- ✅ Bit manipulation pattern
- ✅ Event emission

### Improvements
- 🔄 Cleaner, more focused interface
- 🔄 Better documentation and naming
- 🔄 More comprehensive test suite
- 🔄 Gas-optimized view functions
- 🔄 Removed backward compatibility constraints

## Usage Examples

### Deploy and Setup
```solidity
// Deploy with owner and EAS address
AttestationTracker tracker = new AttestationTracker(owner, easAddress);

// Mark a multisig as active
tracker.setMultisigActiveStatus(multisigAddr, true);
```

### Making Attestations
```solidity
// Create attestation request
IEAS.DelegatedAttestationRequest memory request = IEAS.DelegatedAttestationRequest({
    schema: schemaUID,
    data: abi.encode("attestation data"),
    expirationTime: uint64(block.timestamp + 3600),
    revocable: true,
    refUID: bytes32(0),
    recipient: recipientAddr,
    value: 0,
    deadline: uint64(block.timestamp + 1800),
    signature: signatureBytes
});

// Submit through tracker (increments count and forwards to EAS)
bytes32 attestationUID = tracker.attestByDelegation(request);
```

### Querying State
```solidity
// Get attestation count
uint256 count = tracker.getNumAttestations(multisigAddr);

// Check active status
bool isActive = tracker.isMultisigActive(multisigAddr);

// Get both efficiently
(uint256 attestations, bool active) = tracker.getMultisigInfo(multisigAddr);
```

## Network Compatibility

This contract is designed to work on any network where EAS is deployed:
- Ethereum Mainnet
- Arbitrum
- Optimism  
- Polygon
- Base
- Other EVM networks with EAS deployment

## License

MIT License - see LICENSE file for details.