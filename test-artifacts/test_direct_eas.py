#!/usr/bin/env python3

import os
import sys
sys.path.append('./backend')

from web3 import Web3
from eth_account import Account

# Test direct EAS call
REAL_SCHEMA_UID = "0x4b646acb1d459357d3be21287c81da4026e8440b7283efbab2d124c54478b429"
EAS_CONTRACT_ADDRESS = "0x4200000000000000000000000000000000000021"
PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
account = Account.from_key(PRIVATE_KEY)

print(f"🧪 Testing DIRECT EAS call with schema: {REAL_SCHEMA_UID}")

# Encode test data
encoded_data = w3.codec.encode(
    ["string", "string", "uint256", "bytes32"],
    [
        "test-proposal-id",
        "test-dao.eth", 
        1,
        Web3.to_bytes(hexstr="0x" + "a" * 64),
    ],
)

# Create minimal delegated request
delegated_request = {
    "schema": Web3.to_bytes(hexstr=REAL_SCHEMA_UID),
    "data": encoded_data,
    "expirationTime": 0,
    "revocable": True,
    "refUID": b"\x00" * 32,
    "recipient": account.address,
    "value": 0,
    "deadline": 0,
    "signature": b"",
}

print(f"📝 Request: {delegated_request}")

# EAS ABI for attestByDelegation
eas_abi = [
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
                "name": "request",
                "type": "tuple"
            }
        ],
        "name": "attestByDelegation",
        "outputs": [{"name": "", "type": "bytes32"}],
        "type": "function"
    }
]

eas_contract = w3.eth.contract(
    address=Web3.to_checksum_address(EAS_CONTRACT_ADDRESS),
    abi=eas_abi
)

try:
    print("🔧 Testing direct EAS.attestByDelegation()...")
    
    # Build transaction
    tx = eas_contract.functions.attestByDelegation(
        delegated_request
    ).build_transaction({
        'from': account.address,
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
    })
    
    print(f"📝 EAS transaction built successfully")
    
    # Try to estimate gas
    gas_estimate = w3.eth.estimate_gas(tx)
    print(f"⛽ EAS gas estimate: {gas_estimate}")
    print("✅ EAS call should work!")
    
except Exception as e:
    print(f"❌ EAS direct call failed: {str(e)}")
    
    # Maybe the issue is with signature validation or deadline
    print("🔍 Let's check if it's a signature/deadline issue...")
    
    # Try with a future deadline
    delegated_request["deadline"] = int(w3.eth.get_block('latest')['timestamp'] + 3600)
    
    try:
        tx = eas_contract.functions.attestByDelegation(
            delegated_request
        ).build_transaction({
            'from': account.address,
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
        })
        
        gas_estimate = w3.eth.estimate_gas(tx)
        print(f"⛽ EAS with future deadline works! Gas: {gas_estimate}")
        
    except Exception as e2:
        print(f"❌ Still failing with future deadline: {str(e2)}")
        print("The issue might be that EAS requires a valid signature even for delegated calls")