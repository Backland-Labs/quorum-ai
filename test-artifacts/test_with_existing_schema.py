#!/usr/bin/env python3
"""Test EAS attestation using an existing schema on Base mainnet."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from web3 import Web3
from eth_account import Account
import time

def main():
    print("=" * 60)
    print("Testing EAS with Simple Schema")
    print("=" * 60)
    
    w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
    private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    account = Account.from_key(private_key)
    
    # Use a very simple schema for testing
    # Let's create and register a simple bool schema
    SCHEMA_REGISTRY = "0x4200000000000000000000000000000000000020"
    SIMPLE_SCHEMA = "bool isTrue"
    
    print(f"\n1. Registering simple schema: {SIMPLE_SCHEMA}")
    
    # Register simple schema
    abi = [{
        "inputs": [
            {"name": "schema", "type": "string"},
            {"name": "resolver", "type": "address"}, 
            {"name": "revocable", "type": "bool"}
        ],
        "name": "register",
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }]
    
    contract = w3.eth.contract(address=SCHEMA_REGISTRY, abi=abi)
    
    tx = contract.functions.register(
        SIMPLE_SCHEMA,
        "0x0000000000000000000000000000000000000000",
        True
    ).build_transaction({
        'from': account.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
    })
    
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status == 1:
        print("   ✅ Simple schema registered!")
        
        # Calculate schema UID
        from eth_utils import keccak
        encoded = w3.codec.encode(
            ["string", "address", "bool"],
            [SIMPLE_SCHEMA, "0x0000000000000000000000000000000000000000", True]
        )
        schema_uid = keccak(encoded)
        print(f"   Schema UID: 0x{schema_uid.hex()}")
        
        # Now test attestation with this schema
        print(f"\n2. Testing attestation with simple schema")
        
        EAS_CONTRACT = "0x4200000000000000000000000000000000000021"
        
        # EAS attest function ABI
        eas_abi = [{
            "inputs": [{
                "components": [
                    {"name": "schema", "type": "bytes32"},
                    {"name": "data", "type": "bytes"},
                    {"name": "recipient", "type": "address"},
                    {"name": "expirationTime", "type": "uint64"},
                    {"name": "revocable", "type": "bool"},
                    {"name": "refUID", "type": "bytes32"},
                    {"name": "value", "type": "uint256"}
                ],
                "name": "request",
                "type": "tuple"
            }],
            "name": "attest",
            "outputs": [{"name": "", "type": "bytes32"}],
            "stateMutability": "payable",
            "type": "function"
        }]
        
        eas_contract = w3.eth.contract(address=EAS_CONTRACT, abi=eas_abi)
        
        # Simple attestation data (just a bool true)
        attestation_data = w3.codec.encode(["bool"], [True])
        
        # Build attestation request
        attestation_request = {
            "schema": schema_uid,
            "data": attestation_data,
            "recipient": account.address,
            "expirationTime": 0,
            "revocable": True,
            "refUID": b"\x00" * 32,
            "value": 0
        }
        
        # Send attestation
        tx = eas_contract.functions.attest(attestation_request).build_transaction({
            'from': account.address,
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'value': 0
        })
        
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"   TX sent: {tx_hash.hex()}")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print("   ✅ Attestation successful!")
            print(f"   Gas used: {receipt.gasUsed}")
            
            # The attestation UID should be in the logs
            if receipt.logs:
                print(f"   Events: {len(receipt.logs)}")
        else:
            print("   ❌ Attestation failed!")
            
    else:
        print("   ❌ Schema registration failed!")
        # Try with our original schema anyway
        print("\n   Trying with hardcoded schema UID...")
        test_with_hardcoded_schema(w3, account)

def test_with_hardcoded_schema(w3, account):
    """Test with our original schema UID."""
    
    print("\n3. Testing with original schema (may not exist)")
    
    # Our original schema UID
    schema_uid = bytes.fromhex("4b646acb1d459357d3be21287c81da4026e8440b7283efbab2d124c54478b429")
    
    EAS_CONTRACT = "0x4200000000000000000000000000000000000021"
    
    # Test if EAS contract will accept it
    eas_abi = [{
        "inputs": [{
            "components": [
                {"name": "schema", "type": "bytes32"},
                {"name": "data", "type": "bytes"},
                {"name": "recipient", "type": "address"},
                {"name": "expirationTime", "type": "uint64"},
                {"name": "revocable", "type": "bool"},
                {"name": "refUID", "type": "bytes32"},
                {"name": "value", "type": "uint256"}
            ],
            "name": "request",
            "type": "tuple"
        }],
        "name": "attest",
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "payable",
        "type": "function"
    }]
    
    eas_contract = w3.eth.contract(address=EAS_CONTRACT, abi=eas_abi)
    
    # Encode our attestation data
    attestation_data = w3.codec.encode(
        ["string", "string", "uint256", "bytes32"],
        ["test_proposal", "test_space.eth", 1, b"\x00" * 32]
    )
    
    attestation_request = {
        "schema": schema_uid,
        "data": attestation_data,
        "recipient": account.address,
        "expirationTime": 0,
        "revocable": True,
        "refUID": b"\x00" * 32,
        "value": 0
    }
    
    try:
        # Try to estimate gas first
        gas = eas_contract.functions.attest(attestation_request).estimate_gas({
            'from': account.address,
            'value': 0
        })
        print(f"   Gas estimate: {gas}")
        print("   ✅ Schema appears to be valid!")
    except Exception as e:
        print(f"   ❌ Schema not valid: {e}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()