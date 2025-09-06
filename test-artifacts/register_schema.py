#!/usr/bin/env python3
"""Register EAS schema on the forked Base chain and verify it works."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from web3 import Web3
from eth_account import Account
import json

def main():
    # Connect to forked Base
    w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
    print(f"Connected: {w3.is_connected()}")
    print(f"Chain ID: {w3.eth.chain_id}")
    
    # Account
    private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    account = Account.from_key(private_key)
    print(f"Account: {account.address}")
    print(f"Balance: {w3.eth.get_balance(account.address) / 10**18:.4f} ETH")
    
    # Schema Registry address on Base
    SCHEMA_REGISTRY = "0x4200000000000000000000000000000000000020"
    
    # Our schema
    SCHEMA = "string proposal_id,string space_id,uint256 choice,bytes32 vote_tx_hash"
    
    # SchemaRegistry ABI for register function
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
    
    print(f"\n1. Registering schema: {SCHEMA}")
    
    # Build and send transaction
    tx = contract.functions.register(
        SCHEMA,
        "0x0000000000000000000000000000000000000000",  # No resolver
        True  # Revocable
    ).build_transaction({
        'from': account.address,
        'gas': 500000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
    })
    
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"   TX sent: {tx_hash.hex()}")
    
    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status == 1:
        print(f"   ✅ Schema registered!")
        
        # The schema UID should be in the return value
        # We can calculate it manually
        from eth_utils import keccak
        
        # Schema UID = keccak256(abi.encodePacked(schema, resolver, revocable))
        encoded = w3.codec.encode(
            ["string", "address", "bool"],
            [SCHEMA, "0x0000000000000000000000000000000000000000", True]
        )
        schema_uid = keccak(encoded)
        print(f"   Schema UID: 0x{schema_uid.hex()}")
        
        # Verify it matches our expected UID
        expected_uid = "0x4b646acb1d459357d3be21287c81da4026e8440b7283efbab2d124c54478b429"
        if f"0x{schema_uid.hex()}" == expected_uid:
            print(f"   ✅ Schema UID matches expected value!")
        else:
            print(f"   ⚠️  Schema UID mismatch!")
            print(f"      Expected: {expected_uid}")
            print(f"      Got: 0x{schema_uid.hex()}")
            
        return f"0x{schema_uid.hex()}"
    else:
        print(f"   ❌ Registration failed!")
        return None

if __name__ == "__main__":
    schema_uid = main()