# Service Registry Contract

## Contract Address
**Base Mainnet**: `0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE`

## Overview
The Service Registry is a smart contract that manages autonomous services on the Base network. It tracks service configurations, multisig addresses, agent instances, and service states.

## Main Functions

### `getService(uint256 serviceId)`
Returns detailed information about a specific service.

**Returns** (tuple):
- `securityDeposit` (uint96) - Security deposit amount required for the service
- `multisig` (address) - **The Safe/multisig address associated with this service**
- `configHash` (bytes32) - IPFS hash or identifier for service configuration
- `threshold` (uint32) - Number of signatures required for multisig operations
- `maxNumAgentInstances` (uint32) - Maximum number of agent instances allowed
- `numAgentInstances` (uint32) - Current number of active agent instances
- `state` (uint8) - Current service state (see states below)
- `agentIds` (uint32[]) - Array of agent IDs participating in this service

**Service States**:
- `0` - NonExistent
- `1` - PreRegistration
- `2` - ActiveRegistration
- `3` - FinishedRegistration
- `4` - Deployed
- `5` - TerminatedBonded

### `totalSupply()`
Returns the total number of services registered in the contract.

**Returns**: `uint256` - Total count of services

### `exists(uint256 serviceId)`
Checks if a service with the given ID exists.

**Parameters**:
- `serviceId` (uint256) - The service ID to check

**Returns**: `bool` - True if service exists, false otherwise

## Usage Examples

### Query Service Details (using cast)
```bash
export ETH_RPC_URL="https://mainnet.base.org"

# Get service details for service ID 168
cast call 0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE \
  "getService(uint256)(uint96,address,bytes32,uint32,uint32,uint32,uint8,uint32[])" \
  168
```

### Get Total Services
```bash
cast call 0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE \
  "totalSupply()(uint256)"
```

### Check Service Existence
```bash
cast call 0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE \
  "exists(uint256)(bool)" \
  168
```

## Integration Points

This contract is referenced in multiple parts of the codebase:

- `backend/config.py:297` - Default service registry address configuration
- `backend/tests/test_service_discovery_integration.py` - Integration tests for service discovery
- `contracts/script/DeployOurStakingToken.s.sol` - Deployment scripts
- `env/fork.env` - Environment configuration

## Key Use Cases

1. **Service Discovery**: Given a Safe address, iterate through services to find which service ID manages that Safe
2. **Service Monitoring**: Track service states and agent instances
3. **Configuration Lookup**: Retrieve service configuration hashes and thresholds
4. **Agent Management**: View which agents are associated with each service

## Related Documentation

- [Service Discovery Integration Test](../backend/tests/test_service_discovery_integration.py)
- [Contract Test README](../contracts/test/README.md)
