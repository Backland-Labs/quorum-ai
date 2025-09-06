#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "web3",
#     "eth-account",
#     "pydantic",
#     "pydantic-settings",
#     "python-dotenv",
#     "httpx",
#     "safe-eth-py",
#     "pydantic-ai",
# ]
# ///
"""
Test script to verify the updated AttestationTracker interface works correctly.
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from web3 import Web3
from eth_account import Account
from config import settings
from services.safe_service import SafeService
from models import EASAttestationData
from datetime import datetime
import asyncio
import json

def test_new_interface():
    """Test the new AttestationTracker interface with 4 parameters."""
    
    print("Testing new AttestationTracker interface...")
    print(f"AttestationTracker address: {settings.attestation_tracker_address}")
    print(f"EAS contract address: {settings.eas_contract_address}")
    print(f"Safe address: {settings.base_safe_address}")
    
    # Create SafeService instance
    safe_service = SafeService()
    
    # Create test attestation data
    test_data = EASAttestationData(
        agent="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",  # Test address
        space_id="test-space.eth",
        proposal_id="0xtest123",
        vote_choice=1,
        snapshot_sig="0x" + "0" * 64,  # Valid 66-char hash
        timestamp=int(datetime.now().timestamp()),
        run_id="test-run-001",
        confidence=85
    )
    
    print("\nTest attestation data:")
    print(f"  Agent: {test_data.agent}")
    print(f"  Space: {test_data.space_id}")
    print(f"  Proposal: {test_data.proposal_id}")
    print(f"  Vote choice: {test_data.vote_choice}")
    
    try:
        # Build the transaction using the updated method
        print("\nBuilding transaction with new interface...")
        tx_data = safe_service._build_delegated_attestation_tx(
            test_data,
            target_address=settings.attestation_tracker_address,
            abi_name="attestation_tracker"
        )
        
        print("\n✅ Transaction built successfully!")
        print(f"  To: {tx_data['to']}")
        print(f"  Data length: {len(tx_data['data'])} bytes")
        print(f"  Value: {tx_data['value']}")
        
        # Decode the function call to verify it's correct
        from utils.abi_loader import load_abi
        abi = load_abi("attestation_tracker")
        
        # Find the attestByDelegation function in the ABI
        attest_func = None
        for item in abi:
            if item.get("type") == "function" and item.get("name") == "attestByDelegation":
                attest_func = item
                break
        
        if attest_func:
            print("\n✅ Function signature matches new interface:")
            print(f"  Parameters: {len(attest_func['inputs'])} (expected 4)")
            param_names = [p['name'] for p in attest_func['inputs']]
            print(f"  Parameter names: {param_names}")
            assert len(attest_func['inputs']) == 4, "Should have 4 parameters"
            assert param_names == ['delegatedRequest', 'signature', 'attester', 'deadline'], "Parameter names don't match"
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Set test environment variables if not set
    if not os.getenv("ATTESTATION_TRACKER_ADDRESS"):
        os.environ["ATTESTATION_TRACKER_ADDRESS"] = "0xc16647a4290E4C931aD586713c7d85E0eFbafba0"
    if not os.getenv("EAS_CONTRACT_ADDRESS"):
        os.environ["EAS_CONTRACT_ADDRESS"] = "0x4200000000000000000000000000000000000021"
    if not os.getenv("BASE_SAFE_ADDRESS"):
        os.environ["BASE_SAFE_ADDRESS"] = "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca"
    if not os.getenv("ETHEREUM_PRIVATE_KEY"):
        # Use a test private key (DO NOT use in production!)
        os.environ["ETHEREUM_PRIVATE_KEY"] = "0x" + "1" * 64
    if not os.getenv("EAS_SCHEMA_UID"):
        os.environ["EAS_SCHEMA_UID"] = "0x7d917fcbc9a29a9705ff9936ffa599500e4fd902e4486bae317414fe967b307c"
    
    success = test_new_interface()
    sys.exit(0 if success else 1)