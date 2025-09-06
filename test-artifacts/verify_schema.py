#!/usr/bin/env python3
"""Verify if our schema exists in EAS."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from web3 import Web3
from eth_utils import keccak

# Connect
w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

# Calculate our schema UID
SCHEMA = "string proposal_id,string space_id,uint256 choice,bytes32 vote_tx_hash"
RESOLVER = "0x0000000000000000000000000000000000000000"
REVOCABLE = True

# Calculate UID same way EAS does
encoded = w3.codec.encode(
    ["string", "address", "bool"],
    [SCHEMA, RESOLVER, REVOCABLE]
)
schema_uid = keccak(encoded)

print(f"Our schema: {SCHEMA}")
print(f"Calculated UID: 0x{schema_uid.hex()}")
print(f"Expected UID:   0x4b646acb1d459357d3be21287c81da4026e8440b7283efbab2d124c54478b429")
print(f"Match: {schema_uid.hex() == '4b646acb1d459357d3be21287c81da4026e8440b7283efbab2d124c54478b429'}")

# Now check if this schema exists in EAS
EAS = "0x4200000000000000000000000000000000000021"

# Minimal ABI for getSchema
abi = [{
    "inputs": [{"name": "uid", "type": "bytes32"}],
    "name": "getSchema",
    "outputs": [{
        "components": [
            {"name": "uid", "type": "bytes32"},
            {"name": "resolver", "type": "address"},
            {"name": "revocable", "type": "bool"},
            {"name": "schema", "type": "string"}
        ],
        "name": "schemaRecord",
        "type": "tuple"
    }],
    "stateMutability": "view",
    "type": "function"
}]

eas = w3.eth.contract(address=EAS, abi=abi)

print(f"\nChecking if schema exists in EAS...")
try:
    result = eas.functions.getSchema(schema_uid).call()
    print(f"✅ Schema EXISTS in EAS!")
    print(f"   UID: 0x{result[0].hex()}")
    print(f"   Resolver: {result[1]}")
    print(f"   Revocable: {result[2]}")
    print(f"   Schema: {result[3]}")
except Exception as e:
    print(f"❌ Schema not found in EAS: {e}")