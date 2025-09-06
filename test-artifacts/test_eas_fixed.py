#!/usr/bin/env python3
"""Test EAS attestation with the corrected schema UID."""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from services.safe_service import SafeService
from models import EASAttestationData
from web3 import Web3
import json


async def test_eas_attestation():
    """Test EAS attestation creation with corrected configuration."""
    
    print("=" * 60)
    print("Testing EAS Attestation with Corrected Schema")
    print("=" * 60)
    
    # Initialize SafeService
    safe_service = SafeService()
    
    # Create test attestation data
    import time
    test_attestation = EASAttestationData(
        voter_address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",  # First anvil account
        proposal_id="0x123test",
        space_id="test-space.eth",
        choice=1,
        vote_tx_hash="0x" + "0" * 64,  # Dummy tx hash
        timestamp=int(time.time()),
        attestation_uid="",  # Will be filled by EAS
        attestation_tx_hash="0x" + "0" * 64  # Placeholder
    )
    
    print(f"\nTest Attestation Data:")
    print(f"  Voter: {test_attestation.voter_address}")
    print(f"  Proposal: {test_attestation.proposal_id}")
    print(f"  Space: {test_attestation.space_id}")
    print(f"  Choice: {test_attestation.choice}")
    print(f"  Vote TX Hash: {test_attestation.vote_tx_hash}")
    
    # Check configuration from settings
    from config import settings
    print(f"\nConfiguration Check:")
    print(f"  EAS Contract: {settings.eas_contract_address}")
    print(f"  Schema UID: {settings.eas_schema_uid}")
    print(f"  AttestationTracker: {settings.attestation_tracker_address}")
    print(f"  Safe Address: {settings.base_safe_address}")
    
    # Create attestation
    print(f"\nCreating EAS attestation...")
    result = await safe_service.create_eas_attestation(test_attestation)
    
    if result.get("success"):
        print(f"✅ SUCCESS! Attestation created")
        print(f"  Safe TX Hash: {result.get('safe_tx_hash')}")
    else:
        print(f"❌ FAILED! Error: {result.get('error')}")
        
        # If it's a transaction error, try to decode it
        error_msg = result.get('error', '')
        if 'execution reverted' in error_msg.lower():
            print("\n⚠️  Transaction reverted. Possible causes:")
            print("  1. Schema UID doesn't exist in EAS")
            print("  2. Signature verification failed")
            print("  3. Contract permissions issue")
    
    print("\n" + "=" * 60)
    return result


async def verify_schema_exists():
    """Verify the schema exists in EAS contract."""
    from utils.web3_provider import get_w3
    from config import settings
    
    print("\nVerifying schema in EAS contract...")
    
    w3 = get_w3("base")
    eas_address = settings.eas_contract_address
    schema_uid = settings.eas_schema_uid
    
    if not eas_address or not schema_uid:
        print("❌ Missing EAS configuration")
        return False
    
    # Load EAS ABI (simplified check)
    eas_abi = [
        {
            "inputs": [{"name": "uid", "type": "bytes32"}],
            "name": "getSchema",
            "outputs": [{"name": "", "type": "tuple"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(eas_address),
            abi=eas_abi
        )
        
        schema_bytes = Web3.to_bytes(hexstr=schema_uid)
        # This will throw if schema doesn't exist
        result = contract.functions.getSchema(schema_bytes).call()
        print(f"✅ Schema exists in EAS: {schema_uid}")
        return True
    except Exception as e:
        print(f"❌ Schema not found or error: {e}")
        return False


async def main():
    """Main test function."""
    # First verify the schema
    await verify_schema_exists()
    
    # Then test attestation
    result = await test_eas_attestation()
    
    # Exit with appropriate code
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    asyncio.run(main())