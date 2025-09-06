#!/usr/bin/env python3
"""
Simple test to verify AttestationTracker contract functionality
"""

from web3 import Web3
from eth_abi import encode
import json

# Configuration
RPC_URL = "http://localhost:8545"
ATTESTATION_TRACKER_ADDRESS = "0x82372200341a23377129Ccc1aE2EFeB3048440eC"
EAS_CONTRACT_ADDRESS = "0x4200000000000000000000000000000000000021"
SAFE_ADDRESS = "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca"
PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# Initialize web3
w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = w3.eth.account.from_key(PRIVATE_KEY)

# AttestationTracker ABI (minimal)
ATTESTATION_TRACKER_ABI = [
    {
        "inputs": [{"name": "multisig", "type": "address"}],
        "name": "getNumAttestations",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "multisig", "type": "address"}, {"name": "active", "type": "bool"}],
        "name": "setMultisigActiveStatus",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def test_attestation_tracker():
    print("=== Testing AttestationTracker Contract ===")
    
    # Create contract instance
    contract = w3.eth.contract(
        address=ATTESTATION_TRACKER_ADDRESS,
        abi=ATTESTATION_TRACKER_ABI
    )
    
    # Test 1: Check current attestation count
    print(f"1. Checking attestation count for Safe: {SAFE_ADDRESS}")
    current_count = contract.functions.getNumAttestations(SAFE_ADDRESS).call()
    print(f"   Current attestation count: {current_count}")
    
    # Test 2: Set Safe as active (requires owner)
    print(f"2. Setting Safe as active...")
    try:
        tx_hash = contract.functions.setMultisigActiveStatus(SAFE_ADDRESS, True).transact({
            'from': account.address,
            'gas': 100000
        })
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"   Transaction successful: {receipt.transactionHash.hex()}")
    except Exception as e:
        print(f"   Error setting active status: {e}")
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_attestation_tracker()