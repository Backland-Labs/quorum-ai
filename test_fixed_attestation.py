#!/usr/bin/env python3

import os
import sys
sys.path.append('./backend')

from web3 import Web3
from eth_account import Account
import json
from datetime import datetime

# Use the newly registered schema UID
REAL_SCHEMA_UID = "0x4b646acb1d459357d3be21287c81da4026e8440b7283efbab2d124c54478b429"
ATTESTATION_TRACKER_ADDRESS = "0x82372200341a23377129Ccc1aE2EFeB3048440eC"
EAS_CONTRACT_ADDRESS = "0x4200000000000000000000000000000000000021"
PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# Initialize web3 and account
w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
account = Account.from_key(PRIVATE_KEY)

print(f"🧪 Testing attestation with REAL schema UID: {REAL_SCHEMA_UID}")
print(f"Account: {account.address}")

# Create test attestation data matching SafeService encoding
test_data = {
    "proposal_id": "0x123abc456def",
    "space_id": "test-dao.eth", 
    "choice": 1,  # FOR
    "vote_tx_hash": "0x" + "a" * 64,  # 32-byte hash
}

# Encode data exactly like SafeService._encode_attestation_data()
encoded_data = w3.codec.encode(
    ["string", "string", "uint256", "bytes32"],
    [
        test_data["proposal_id"],
        test_data["space_id"],
        test_data["choice"],
        Web3.to_bytes(hexstr=test_data["vote_tx_hash"]),
    ],
)

print(f"✅ Encoded data: {encoded_data.hex()}")

# Create delegated request using real schema
delegated_request = {
    "schema": Web3.to_bytes(hexstr=REAL_SCHEMA_UID),
    "data": encoded_data,
    "expirationTime": 0,
    "revocable": True,
    "refUID": b"\x00" * 32,
    "recipient": Web3.to_checksum_address(account.address),
    "value": 0,
    "deadline": 0,
    "signature": b"",  # Empty for Safe multisig pattern
}

# Load AttestationTracker ABI (simple interface)
attestation_tracker_abi = [
    {
        "inputs": [
            {
                "components": [
                    {"name": "schema", "type": "bytes32"},
                    {"name": "data", "type": "bytes"},
                    {"name": "expirationTime", "type": "uint64"},
                    {"name": "revocable", "type": "bool"},
                    {"name": "refUID", "type": "bytes32"},
                    {"name": "recipient", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "deadline", "type": "uint64"},
                    {"name": "signature", "type": "bytes"}
                ],
                "name": "delegatedRequest",
                "type": "tuple"
            }
        ],
        "name": "attestByDelegation",
        "outputs": [{"name": "", "type": "bytes32"}],
        "type": "function"
    }
]

attestation_tracker = w3.eth.contract(
    address=Web3.to_checksum_address(ATTESTATION_TRACKER_ADDRESS),
    abi=attestation_tracker_abi
)

print("\n🔧 Testing AttestationTracker.attestByDelegation() with real schema...")

try:
    # Build transaction
    tx = attestation_tracker.functions.attestByDelegation(
        delegated_request
    ).build_transaction({
        'from': account.address,
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
    })
    
    print(f"📝 Transaction built successfully")
    
    # Estimate gas
    gas_estimate = w3.eth.estimate_gas(tx)
    print(f"⛽ Gas estimate: {gas_estimate}")
    
    # Sign and send
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    print(f"📤 Transaction sent: {tx_hash.hex()}")
    
    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status == 1:
        print("🎉 ✅ ATTESTATION SUCCESS! The fix worked!")
        print(f"📜 Transaction hash: {tx_hash.hex()}")
        print(f"⛽ Gas used: {receipt['gasUsed']}")
        
        # Check attestation count increased
        attestation_count = attestation_tracker.functions.getNumAttestations(account.address).call()
        print(f"📊 New attestation count: {attestation_count}")
        
    else:
        print("❌ Transaction failed")
        print(f"Receipt: {receipt}")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()