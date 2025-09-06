#!/usr/bin/env python3
"""Check if a schema exists in the registry."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from web3 import Web3

def main():
    w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
    
    SCHEMA_REGISTRY = "0x4200000000000000000000000000000000000020"
    
    # Get the schema UID we're checking
    schema_uid = input("Enter schema UID to check (with 0x): ")
    
    # Check if schema exists
    registry_abi = [{
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
    
    registry = w3.eth.contract(address=SCHEMA_REGISTRY, abi=registry_abi)
    
    try:
        result = registry.functions.getSchema(bytes.fromhex(schema_uid[2:])).call()
        print(f"\nSchema found!")
        print(f"  UID: {result[0].hex()}")
        print(f"  Resolver: {result[1]}")
        print(f"  Revocable: {result[2]}")
        print(f"  Schema: {result[3]}")
        
        # Check if UID is non-zero
        if result[0] == b'\x00' * 32:
            print("\n⚠️  Schema UID is all zeros - schema not registered!")
        else:
            print("\n✅ Schema is registered!")
    except Exception as e:
        print(f"Error checking schema: {e}")

if __name__ == "__main__":
    main()