# AttestationTracker Contract Integration Implementation Plan

## Overview

Integrate the AttestationTracker.sol smart contract as a wrapper around the existing EAS (Ethereum Attestation Service) attestations in the quorum-ai backend. This will add multisig activity tracking capabilities while maintaining backward compatibility with the current voting and attestation workflow.

## Current State Analysis

The backend currently has a complete EAS integration that creates on-chain attestations for Snapshot votes through Safe multisig transactions. The AttestationTracker contract provides a wrapper around EAS that adds multisig tracking with efficient bit manipulation storage (MSB for active status, lower 255 bits for count).

### Critical Discovery:
**The AttestationTracker uses the SAME `attestByDelegation()` interface as EAS with `DelegatedAttestationRequest` struct, NOT the `attest()` method with `AttestationRequest` struct that the current implementation uses.** This requires updating the transaction building logic to use the delegated pattern.

## Desired End State

After implementation, the system will route attestations through the AttestationTracker contract when configured, enabling:
- Automatic tracking of attestation counts per multisig
- Active/inactive status management for multisigs  
- Complete backward compatibility with existing voting workflow
- No changes required to the frontend or API
- Proper integration with existing retry/checkpoint system

### Key Discoveries:
- Current EAS integration uses `attest()` method: `backend/services/safe_service.py:520`
- AttestationTracker requires `attestByDelegation()`: `contracts/src/AttestationTracker.sol:90`
- Existing retry mechanism with MAX_ATTESTATION_RETRIES=3: `backend/services/agent_run_service.py:986`
- State management through checkpoints: `backend/services/agent_run_service.py:956-1099`
- Existing `load_abi()` utility: `backend/utils/abi_loader.py:30`

## What We're NOT Doing

- NOT creating new service classes (use helper functions instead)
- NOT creating new ABI loader methods (use existing `load_abi()`)
- NOT making monitoring functions async (web3 calls are sync)
- NOT creating new API endpoints (add to existing health endpoint)
- NOT creating new test files (extend existing tests)
- NOT migrating existing attestations
- NOT modifying frontend or API interfaces
- NOT changing the Safe multisig transaction pattern
- NOT adding enable/disable flags (use address presence)
- NOT adding allowlist configuration (not needed)
- NOT deploying to Mainnet

## Implementation Approach

Minimal modification strategy: Update the existing SafeService to use the delegated attestation pattern and conditionally route through AttestationTracker when the address is configured. Add simple helper functions for monitoring. Reuse all existing patterns and infrastructure.

## Phase 1: Backend Configuration Updates ✅ COMPLETED

### Overview
Update backend configuration to support AttestationTracker address.

### Implementation Summary:
- **Added AttestationTracker address field** to `backend/config.py` after line 329
- **Added Pydantic validator** with Web3.is_address() validation and checksum conversion
- **Updated .env.example** with new optional environment variable
- **Added comprehensive test suite** with 6 test cases covering all scenarios
- **Applied linting and code formatting** for consistency

### Changes Made:

#### 1. Configuration Model Updated
**File**: `backend/config.py`
```python
# AttestationTracker Configuration  
attestation_tracker_address: Optional[str] = Field(
    default=None,
    alias="ATTESTATION_TRACKER_ADDRESS",
    description="AttestationTracker wrapper contract address on Base network. If set, attestations will be routed through this contract.",
)
```

#### 2. Validation Added
**File**: `backend/config.py`
```python
@model_validator(mode='after')
def validate_attestation_tracker_config(self):
    """Validate AttestationTracker configuration."""
    if self.attestation_tracker_address:
        # Validate address format - must be a valid Web3 address
        if not Web3.is_address(self.attestation_tracker_address):
            raise ValueError(f"Invalid ATTESTATION_TRACKER_ADDRESS: {self.attestation_tracker_address}")
        # Convert to checksum address for consistency
        self.attestation_tracker_address = Web3.to_checksum_address(self.attestation_tracker_address)
    return self
```

#### 3. Environment Variable Added
**File**: `.env.example`
```bash
# AttestationTracker Configuration (optional)
ATTESTATION_TRACKER_ADDRESS=  # Deployed AttestationTracker address. If set, attestations will route through it.
```

#### 4. Test Suite Added
**File**: `backend/tests/test_config.py`
- 6 comprehensive tests covering all validation scenarios
- Tests for valid/invalid addresses, checksum conversion, empty values
- All tests passing successfully

### Success Criteria: ✅ VERIFIED

#### Automated Verification: ✅
- ✅ Configuration loads without errors: `uv run python -c "from config import settings; print(settings)"`  
- ✅ Tests pass with new config: `uv run pytest tests/test_config.py::TestAttestationTrackerConfiguration -v`
- ✅ Environment validation works: `uv run pytest tests/test_environment_validation.py -v`

#### Manual Verification: ✅
- ✅ Application starts with new configuration
- ✅ Configuration correctly validates tracker address when provided
- ✅ Code formatted and linted properly

**Implementation Date**: 2025-01-27  
**Status**: COMPLETED

---

## Phase 2: Web3 Provider Extraction

### Overview
Extract web3 provider logic to a shared utility for reuse across services.

### Changes Required:

#### 1. Create Web3 Provider Utility
**File**: `backend/utils/web3_provider.py`
**Changes**: New utility for shared web3 instance management
```python
"""Shared Web3 provider utility for blockchain interactions."""
from web3 import Web3
from typing import Optional
from config import settings
import logging

logger = logging.getLogger(__name__)

def get_w3(chain: str = "base") -> Web3:
    """Get Web3 instance for a specific chain.
    
    Args:
        chain: The chain name (e.g., 'base', 'ethereum')
        
    Returns:
        Web3 instance connected to the chain
        
    Raises:
        ValueError: If no RPC endpoint configured for chain
    """
    # Map chain to RPC endpoint
    rpc_endpoints = {
        "base": settings.get_base_rpc_endpoint(),
        "ethereum": settings.ethereum_rpc_url,
    }
    
    rpc_url = rpc_endpoints.get(chain)
    if not rpc_url:
        raise ValueError(f"No RPC endpoint configured for chain: {chain}")
    
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        logger.warning(f"Web3 provider for {chain} not connected, retrying...")
        # Provider will retry on next call
    
    return w3
```

### Success Criteria:

#### Automated Verification:
- [ ] Utility imports correctly: `uv run python -c "from utils.web3_provider import get_w3"`
- [ ] Web3 instance creation works: `uv run python -c "from utils.web3_provider import get_w3; w3 = get_w3('base')"`

---

## Phase 3: SafeService Integration

### Overview
Update SafeService to handle both direct EAS and AttestationTracker delegated patterns.

### Changes Required:

#### 1. Update SafeService Transaction Builder
**File**: `backend/services/safe_service.py`
**Changes**: Replace `_build_eas_attestation_tx` method (lines 480-527)
```python
def _build_eas_attestation_tx(self, attestation_data: EASAttestationData) -> Dict[str, Any]:
    """Build attestation transaction data.
    
    Routes to AttestationTracker when configured, otherwise uses direct EAS.
    Both use the delegated attestation pattern for Safe multisig compatibility.
    """
    from utils.web3_provider import get_w3
    
    w3 = get_w3("base")
    
    # Use AttestationTracker if configured, otherwise direct EAS
    if settings.attestation_tracker_address:
        return self._build_delegated_attestation_tx(
            attestation_data, 
            target_address=settings.attestation_tracker_address,
            abi_name="attestation_tracker"
        )
    else:
        # Build delegated request for direct EAS (updating from current attest() pattern)
        return self._build_delegated_attestation_tx(
            attestation_data,
            target_address=settings.eas_contract_address,
            abi_name="eas"
        )

def _build_delegated_attestation_tx(
    self, 
    attestation_data: EASAttestationData,
    target_address: str,
    abi_name: str
) -> Dict[str, Any]:
    """Build delegated attestation transaction.
    
    Args:
        attestation_data: The attestation data
        target_address: Contract address to call
        abi_name: Name of ABI file to load
        
    Returns:
        Transaction data dict
    """
    from utils.web3_provider import get_w3
    from utils.abi_loader import load_abi
    
    w3 = get_w3("base")
    
    # Load ABI using existing utility
    contract_abi = load_abi(abi_name)
    
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(target_address),
        abi=contract_abi
    )
    
    # Build delegated attestation request
    delegated_request = {
        "schema": Web3.to_bytes(hexstr=settings.eas_schema_uid),
        "data": self._encode_attestation_data(attestation_data),
        "expirationTime": 0,
        "revocable": True, 
        "refUID": b"\x00" * 32,
        "recipient": Web3.to_checksum_address(attestation_data.voter_address),
        "value": 0,
        "deadline": 0,
        "signature": b""  # Empty for Safe multisig pattern
    }
    
    self.logger.info(
        f"Building delegated attestation for {abi_name} at {target_address[:10]}..."
    )
    
    # Build transaction
    tx = contract.functions.attestByDelegation(delegated_request).build_transaction({
        "from": settings.base_safe_address,
        "gas": 300000,  # Standard gas limit
    })
    
    return {"to": tx["to"], "data": tx["data"], "value": tx.get("value", 0)}
```

#### 2. Remove obsolete _load_eas_abi method
**File**: `backend/services/safe_service.py`
**Changes**: Remove lines 559-570 (replaced by using utils.abi_loader)

### Success Criteria:

#### Automated Verification:
- [ ] SafeService tests pass: `uv run pytest tests/test_safe_service_eas.py -v`
- [ ] Integration tests pass: `uv run pytest tests/test_agent_run_attestation.py -v`
- [ ] ABI loading works: `uv run python -c "from utils.abi_loader import load_abi; abi = load_abi('attestation_tracker')"`

#### Manual Verification:
- [ ] Attestations route through AttestationTracker when address is configured
- [ ] Attestations use delegated pattern for both paths
- [ ] Direct EAS still works when AttestationTracker not configured

---

## Phase 4: Testing Integration

### Overview
Extend existing tests to cover AttestationTracker integration.

### Changes Required:

#### 1. Extend SafeService Tests
**File**: `backend/tests/test_safe_service_eas.py`
**Changes**: Add tests for AttestationTracker routing
```python
# Add to existing test file

@pytest.mark.asyncio
async def test_attestation_routing_with_tracker_configured(mock_safe_service):
    """Test that attestations route through wrapper when address configured."""
    with patch('config.settings.attestation_tracker_address', '0x123'):
        # Test that _build_delegated_attestation_tx is called with tracker address
        # Existing test structure can be extended
        pass

@pytest.mark.asyncio  
async def test_attestation_routing_without_tracker(mock_safe_service):
    """Test that attestations go directly to EAS when wrapper not configured."""
    with patch('config.settings.attestation_tracker_address', None):
        # Test that _build_delegated_attestation_tx is called with EAS address
        # Existing test structure can be extended
        pass
```

#### 2. Extend Agent Run Tests
**File**: `backend/tests/test_agent_run_attestation.py`
**Changes**: Add test for retry mechanism with wrapper
```python
# Add to existing test file

@pytest.mark.asyncio
async def test_attestation_retry_with_tracker(agent_run_service):
    """Test that attestation retries work with AttestationTracker."""
    # Test that failures trigger retry mechanism
    # Test that MAX_ATTESTATION_RETRIES is respected
    # Test that pending_attestations queue is updated correctly
    pass
```

#### 3. Create End-to-End Test Script
**File**: `backend/scripts/test_attestation_tracker_e2e.py`
**Changes**: Script for manual testing
```python
#!/usr/bin/env python3
"""End-to-end test for AttestationTracker integration."""
import asyncio
import os
from datetime import datetime, timezone
from services.safe_service import SafeService
from models import EASAttestationData
from utils.attestation_tracker_helpers import get_multisig_info
from config import settings

async def test_attestation_flow():
    """Test complete attestation flow through wrapper."""
    print(f"Testing AttestationTracker integration...")
    print(f"Wrapper configured: {bool(settings.attestation_tracker_address)}")
    print(f"Wrapper address: {settings.attestation_tracker_address}")
    print(f"Safe address: {settings.base_safe_address}")
    
    if settings.attestation_tracker_address:
        # Check initial statistics
        count_before, is_active = get_multisig_info(settings.base_safe_address)
        print(f"Before: count={count_before}, active={is_active}")
    
    # Create test attestation
    attestation = EASAttestationData(
        proposal_id="test_proposal_123",
        space_id="test.eth",
        voter_address=settings.agent_address or "0x742d35Cc6634C0532925a3b844Bc9e7595f89590",
        choice=1,
        vote_tx_hash="0x" + "0" * 64,
        timestamp=datetime.now(timezone.utc),
        retry_count=0
    )
    
    # Submit through SafeService
    safe_service = SafeService()
    result = await safe_service.create_eas_attestation(attestation)
    print(f"Attestation result: {result}")
    
    if result.get("success") and settings.attestation_tracker_address:
        # Check updated statistics (may not be immediate if Safe tx pending)
        count_after, is_active = get_multisig_info(settings.base_safe_address)
        print(f"After: count={count_after}, active={is_active}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_attestation_flow())
```

### Success Criteria:

#### Automated Verification:
- [ ] Extended SafeService tests pass: `uv run pytest tests/test_safe_service_eas.py -v`
- [ ] Extended agent run tests pass: `uv run pytest tests/test_agent_run_attestation.py -v`
- [ ] All existing tests still pass: `uv run pytest`
- [ ] E2E script runs: `uv run python scripts/test_attestation_tracker_e2e.py`

#### Manual Verification:
- [ ] Complete voting flow works with wrapper configured
- [ ] Attestations appear on-chain through wrapper
- [ ] Statistics accurately reflect attestation activity
- [ ] Retry mechanism works with wrapper failures
- [ ] No regressions in existing functionality

---

## Testing Strategy

### Unit Tests:
- Test configuration validation with tracker address
- Test SafeService routing logic (wrapper vs direct)
- Test delegated attestation transaction building

### Integration Tests:
- Test complete attestation flow with wrapper configured
- Test backward compatibility without wrapper
- Test Safe transaction creation for both modes

### Manual Testing Steps:
1. Deploy AttestationTracker to Base testnet
2. Run test vote without configuring tracker address (verify existing flow)
3. Configure backend with tracker address
4. Submit test vote through wrapper
5. Verify attestation appears on-chain
6. Query statistics via health endpoint
7. Test failure/retry scenario
8. Verify production readiness

## Performance Considerations

- AttestationTracker adds minimal gas overhead (~10k gas for tracking)
- Single storage slot per multisig ensures efficiency
- Sync web3 calls for monitoring (no unnecessary async wrappers)
- Reuse existing web3 providers and ABI loaders
- No impact on frontend performance (backend only)

## Migration Notes

### Simple Configuration:
```bash
# Without AttestationTracker (existing flow)
ATTESTATION_TRACKER_ADDRESS=  # Leave empty

# With AttestationTracker (new flow)
ATTESTATION_TRACKER_ADDRESS=0x...  # Set to deployed contract address
```

### No Data Migration Required:
- Existing attestations remain on EAS
- New attestations go through wrapper when configured
- No need to migrate historical data

## References

- Original research: `research/attestation-tracker-integration.md`
- Contract implementation: `contracts/src/AttestationTracker.sol`
- Existing EAS integration: `backend/services/safe_service.py:436-563`
- Retry mechanism: `backend/services/agent_run_service.py:956-1099`
- ABI utility: `backend/utils/abi_loader.py`
- Web3 patterns: Throughout SafeService and QuorumTrackerService