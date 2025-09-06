#!/usr/bin/env python3

import os
from web3 import Web3
from eth_account import Account
import json
from datetime import datetime

# Contract addresses from environment
ATTESTATION_TRACKER_ADDRESS = "0x82372200341a23377129Ccc1aE2EFeB3048440eC"
EAS_CONTRACT_ADDRESS = "0x4200000000000000000000000000000000000021"
PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# Initialize web3 and account
w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
account = Account.from_key(PRIVATE_KEY)

print(f"Using account: {account.address}")
print(f"AttestationTracker: {ATTESTATION_TRACKER_ADDRESS}")
print(f"EAS: {EAS_CONTRACT_ADDRESS}")

# Load AttestationTracker ABI
with open("contracts/abi/attestation_tracker.json", "r") as f:
    attestation_tracker_abi = json.load(f)

# Create contract instance
attestation_tracker = w3.eth.contract(
    address=Web3.to_checksum_address(ATTESTATION_TRACKER_ADDRESS),
    abi=attestation_tracker_abi
)

# Create test attestation data
test_attestation_data = {
    "proposal_id": "0x123abc...",
    "space_id": "test-dao.eth", 
    "voter_address": account.address,
    "choice": 1,  # FOR
    "vote_tx_hash": "0x" + "a" * 64,  # Mock transaction hash
    "timestamp": datetime.now()
}

# EAS Schema UID from settings (this should match your actual schema)
EAS_SCHEMA_UID = "0x" + "1" * 64  # Mock schema UID for testing

# Encode attestation data (mimicking SafeService._encode_attestation_data)
encoded_data = w3.codec.encode(
    ["string", "string", "uint256", "bytes32"],
    [
        test_attestation_data["proposal_id"],
        test_attestation_data["space_id"],
        test_attestation_data["choice"],
        Web3.to_bytes(hexstr=test_attestation_data["vote_tx_hash"]),
    ],
)

print(f"Encoded attestation data: {encoded_data.hex()}")

# Create delegated request (mimicking SafeService._build_delegated_attestation_tx)
delegated_request = {
    "schema": Web3.to_bytes(hexstr=EAS_SCHEMA_UID),
    "data": encoded_data,
    "expirationTime": 0,
    "revocable": True,
    "refUID": b"\x00" * 32,
    "recipient": Web3.to_checksum_address(test_attestation_data["voter_address"]),
    "value": 0,
    "deadline": 0,
    "signature": b"",  # Empty for Safe multisig pattern
}

print(f"Delegated request: {delegated_request}")

# Test 1: Check if we can call attestByDelegation from the account
print("\n=== Test 1: Direct call to AttestationTracker ===")
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
    
    print(f"Transaction built successfully: {tx}")
    
    # Try to estimate gas
    gas_estimate = w3.eth.estimate_gas(tx)
    print(f"Gas estimate: {gas_estimate}")
    
    # Sign and send transaction
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
    
    print(f"Transaction sent: {tx_hash.hex()}")
    
    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction receipt: {receipt}")
    
    if receipt.status == 1:
        print("✅ AttestationTracker call succeeded!")
    else:
        print("❌ AttestationTracker call failed!")
        
except Exception as e:
    print(f"❌ AttestationTracker call failed with error: {str(e)}")

# Test 2: Check if we can call EAS directly  
print("\n=== Test 2: Direct call to EAS ===")
try:
    # Load EAS ABI
    with open("contracts/abi/eas.json", "r") as f:
        eas_abi = json.load(f)
    
    eas_contract = w3.eth.contract(
        address=Web3.to_checksum_address(EAS_CONTRACT_ADDRESS),
        abi=eas_abi
    )
    
    # Build transaction for direct EAS call
    tx = eas_contract.functions.attestByDelegation(
        delegated_request
    ).build_transaction({
        'from': account.address,
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
    })
    
    print(f"EAS transaction built successfully")
    
    # Try to estimate gas
    gas_estimate = w3.eth.estimate_gas(tx)
    print(f"EAS gas estimate: {gas_estimate}")
    
except Exception as e:
    print(f"❌ Direct EAS call failed with error: {str(e)}")

print("\n=== Test 3: Check contract state ===")
try:
    # Check AttestationTracker state
    owner = attestation_tracker.functions.owner().call()
    eas_address = attestation_tracker.functions.EAS().call()
    num_attestations = attestation_tracker.functions.getNumAttestations(account.address).call()
    
    print(f"AttestationTracker owner: {owner}")
    print(f"AttestationTracker EAS address: {eas_address}")
    print(f"Current attestations for {account.address}: {num_attestations}")
    
    # Check if the schema exists in EAS (this might fail if schema doesn't exist)
    try:
        schema_record = eas_contract.functions.getSchema(Web3.to_bytes(hexstr=EAS_SCHEMA_UID)).call()
        print(f"Schema record: {schema_record}")
    except Exception as e:
        print(f"⚠️  Schema check failed: {str(e)}")
        print("This might indicate the schema doesn't exist or the schema UID is wrong")
        
except Exception as e:
    print(f"❌ Contract state check failed: {str(e)}")