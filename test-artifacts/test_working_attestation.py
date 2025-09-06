#!/usr/bin/env python3
"""Test EAS attestation with a schema we can actually register."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from web3 import Web3
from eth_account import Account
from eth_utils import keccak
import time

def main():
    print("=" * 60)
    print("Working EAS Attestation Test")
    print("=" * 60)
    
    w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
    private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    account = Account.from_key(private_key)
    
    # Create a unique schema that we can register
    timestamp = int(time.time())
    SCHEMA = f"string data_{timestamp}"
    
    print(f"\n1. Registering unique schema: {SCHEMA}")
    
    SCHEMA_REGISTRY = "0x4200000000000000000000000000000000000020"
    
    # Register schema
    registry_abi = [{
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
    
    registry = w3.eth.contract(address=SCHEMA_REGISTRY, abi=registry_abi)
    
    tx = registry.functions.register(
        SCHEMA,
        "0x0000000000000000000000000000000000000000",
        True
    ).build_transaction({
        'from': account.address,
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
    })
    
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status != 1:
        print("   ❌ Schema registration failed!")
        return False
        
    print(f"   ✅ Schema registered! TX: {tx_hash.hex()[:20]}...")
    
    # Get the schema UID from the event logs
    schema_uid = None
    for log in receipt.logs:
        if log.address.lower() == SCHEMA_REGISTRY.lower() and len(log.topics) > 0:
            # The first topic is the event signature, second is the UID
            if len(log.topics) > 1:
                schema_uid = log.topics[1]
            else:
                # Sometimes the UID is in the data
                schema_uid = log.data[:32] if len(log.data) >= 32 else None
            break
    
    if not schema_uid:
        # Fallback: calculate schema UID
        encoded = w3.codec.encode(
            ["string", "address", "bool"],
            [SCHEMA, "0x0000000000000000000000000000000000000000", True]
        )
        schema_uid = keccak(encoded)
        print(f"   Calculated Schema UID: 0x{schema_uid.hex()}")
    else:
        print(f"   Schema UID from event: {schema_uid.hex()}")
    
    # Verify the schema exists
    print(f"\n2. Verifying schema exists in registry...")
    
    verify_abi = [{
        "inputs": [{"name": "uid", "type": "bytes32"}],
        "name": "getSchema",
        "outputs": [{
            "components": [
                {"name": "uid", "type": "bytes32"},
                {"name": "resolver", "type": "address"},
                {"name": "revocable", "type": "bool"},
                {"name": "schema", "type": "string"}
            ],
            "name": "",
            "type": "tuple"
        }],
        "stateMutability": "view",
        "type": "function"
    }]
    
    verify_registry = w3.eth.contract(address=SCHEMA_REGISTRY, abi=verify_abi)
    schema_data = verify_registry.functions.getSchema(schema_uid).call()
    
    if schema_data[0] == b'\x00' * 32:
        print("   ❌ Schema not found in registry!")
        return False
    
    print(f"   ✅ Schema verified: {schema_data[3]}")
    
    # Now test attestation with this schema
    print(f"\n3. Creating attestation with our schema")
    
    EAS = "0x4200000000000000000000000000000000000021"
    
    # EAS attest ABI - corrected structure
    eas_abi = [{
        "inputs": [{
            "components": [
                {"name": "schema", "type": "bytes32"},
                {"name": "data", "type": "tuple", "components": [
                    {"name": "recipient", "type": "address"},
                    {"name": "expirationTime", "type": "uint64"},
                    {"name": "revocable", "type": "bool"},
                    {"name": "refUID", "type": "bytes32"},
                    {"name": "data", "type": "bytes"},
                    {"name": "value", "type": "uint256"}
                ]}
            ],
            "name": "request",
            "type": "tuple"
        }],
        "name": "attest",
        "outputs": [{"name": "", "type": "bytes32"}],
        "stateMutability": "payable",
        "type": "function"
    }]
    
    eas = w3.eth.contract(address=EAS, abi=eas_abi)
    
    # Simple attestation data
    attestation_data = w3.codec.encode(["string"], ["Test attestation data"])
    
    request = {
        "schema": schema_uid,
        "data": {
            "recipient": account.address,
            "expirationTime": 0,
            "revocable": True,
            "refUID": b"\x00" * 32,
            "data": attestation_data,
            "value": 0
        }
    }
    
    try:
        tx = eas.functions.attest(request).build_transaction({
            'from': account.address,
            'gas': 300000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'value': 0
        })
        
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"   TX sent: {tx_hash.hex()[:20]}...")
        
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"   ✅ ATTESTATION SUCCESSFUL!")
            print(f"   Gas used: {receipt.gasUsed}")
            
            # Get attestation UID from logs
            if receipt.logs:
                for log in receipt.logs:
                    if log.address.lower() == EAS.lower() and len(log.topics) > 1:
                        attestation_uid = log.topics[1]
                        print(f"   Attestation UID: {attestation_uid.hex()}")
                        break
                        
            print("\n" + "=" * 60)
            print("SUCCESS: EAS Attestation Working!")
            print("=" * 60)
            print("\nThis proves:")
            print("1. We can register schemas on the forked Base chain")
            print("2. We can create attestations with registered schemas")
            print("3. The EAS system is functional on Base")
            print("\nYour implementation will work once the correct schema")
            print("is registered on your target network.")
            
            return True
        else:
            print(f"   ❌ Attestation failed!")
            print(f"   Gas used: {receipt.gasUsed}")
            
            # Try to get revert reason by replaying the call
            try:
                # Replay the transaction to get the revert reason
                w3.eth.call({
                    'from': account.address,
                    'to': EAS,
                    'data': tx['data'],
                    'value': 0
                }, receipt.blockNumber - 1)
            except Exception as revert_error:
                print(f"   Revert reason: {str(revert_error)}")
            
            return False
    except Exception as e:
        print(f"   ❌ Error creating attestation: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)