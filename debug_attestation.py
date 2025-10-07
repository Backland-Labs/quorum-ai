#!/usr/bin/env python3
"""Debug script to call AttestationTracker directly and see the real error."""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from web3 import Web3
from eth_account import Account
from config import settings
from models import EASAttestationData
from services.safe_service import SafeService
from services.key_manager import KeyManager
from utils.web3_provider import get_w3
from utils.abi_loader import load_abi

# Initialize
w3 = get_w3('base')
key_manager = KeyManager()
private_key = key_manager.get_private_key()
account = Account.from_key(private_key)

print(f"EOA Address: {account.address}")
print(f"Safe Address: {settings.base_safe_address}")
print(f"AttestationTracker: {settings.attestation_tracker_address}")
print(f"EAS Address: {settings.eas_contract_address}")

# Create test attestation
attestation_data = EASAttestationData(
    proposal_id="0xtest123",
    space_id="test.eth",
    vote_choice=1,
    agent=account.address,
    snapshot_sig="0xdeadbeef",
    timestamp=1234567890,
    run_id="test-run",
    confidence=80
)

# Initialize SafeService to use its methods
safe_service = SafeService()

# Build the transaction data
print("\n=== Building Transaction ===")
tx_data = safe_service._build_eas_attestation_tx(attestation_data)
print(f"Target: {tx_data['to']}")
print(f"Data length: {len(tx_data['data'])}")

# Load AttestationTracker ABI
tracker_abi = load_abi('attestation_tracker')
tracker = w3.eth.contract(
    address=Web3.to_checksum_address(settings.attestation_tracker_address),
    abi=tracker_abi
)

# Decode the transaction data to see parameters
print("\n=== Decoding Transaction Data ===")
try:
    func_obj, params = tracker.decode_function_input(tx_data['data'])
    print(f"Function: {func_obj.fn_name}")
    print(f"Parameters:")
    for key, value in params.items():
        if isinstance(value, bytes):
            print(f"  {key}: 0x{value.hex()[:40]}... ({len(value)} bytes)")
        else:
            print(f"  {key}: {value}")
except Exception as e:
    print(f"Failed to decode: {e}")

# Try calling from EOA directly (not through Safe)
print("\n=== Attempting Direct Call from EOA ===")
try:
    # Build transaction from EOA
    tx = {
        'from': account.address,
        'to': tx_data['to'],
        'data': tx_data['data'],
        'value': 0,
        'gas': 1000000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
    }
    
    # Try eth_call first to see if it would succeed
    print("Trying eth_call...")
    result = w3.eth.call(tx)
    print(f"✅ Call succeeded! Result: 0x{result.hex()}")
    
    # If call succeeds, try sending the actual transaction
    print("\nSending actual transaction...")
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transaction sent: {tx_hash.hex()}")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt['status'] == 1:
        print(f"✅ Transaction successful! Gas used: {receipt['gasUsed']}")
        # Check attestation count
        count = tracker.functions.getNumAttestations(account.address).call()
        print(f"Attestation count for EOA: {count}")
    else:
        print(f"❌ Transaction failed")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# Try calling from Safe address via eth_call
print("\n=== Attempting Call from Safe Address ===")
try:
    tx_from_safe = {
        'from': settings.base_safe_address,
        'to': tx_data['to'],
        'data': tx_data['data'],
        'value': 0,
    }
    
    result = w3.eth.call(tx_from_safe)
    print(f"✅ Call from Safe succeeded! Result: 0x{result.hex()}")
    
except Exception as e:
    print(f"❌ Error calling from Safe: {e}")
    # Try to extract revert reason
    if hasattr(e, 'args') and len(e.args) > 0:
        print(f"Detailed error: {e.args[0]}")
