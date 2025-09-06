#!/usr/bin/env python3
"""Register the EAS schema on the forked Base chain."""

import sys
from web3 import Web3
from eth_account import Account

# Connect to the forked Base chain
w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

# Load the private key
private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
account = Account.from_key(private_key)

# Schema Registry address on Base
SCHEMA_REGISTRY = "0x4200000000000000000000000000000000000020"

# Schema to register
SCHEMA = "string proposal_id,string space_id,uint256 choice,bytes32 vote_tx_hash"

print(f"Connected to chain: {w3.is_connected()}")
print(f"Chain ID: {w3.eth.chain_id}")
print(f"Account: {account.address}")
print(f"Balance: {w3.eth.get_balance(account.address) / 10**18} ETH")

# Schema Registry ABI (minimal)
abi = [
    {
        "inputs": [
            {"internalType": "string", "name": "schema", "type": "string"},
            {"internalType": "address", "name": "resolver", "type": "address"},
            {"internalType": "bool", "name": "revocable", "type": "bool"}
        ],
        "name": "register",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Create contract instance
schema_registry = w3.eth.contract(
    address=Web3.to_checksum_address(SCHEMA_REGISTRY),
    abi=abi
)

print(f"\nRegistering schema: {SCHEMA}")
print(f"Resolver: 0x0000000000000000000000000000000000000000")
print(f"Revocable: True")

# Build transaction
tx = schema_registry.functions.register(
    SCHEMA,
    "0x0000000000000000000000000000000000000000",  # No resolver
    True  # Revocable
).build_transaction({
    'from': account.address,
    'gas': 500000,
    'gasPrice': w3.eth.gas_price,
    'nonce': w3.eth.get_transaction_count(account.address),
})

# Sign and send transaction
signed_tx = account.sign_transaction(tx)
tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

print(f"\nTransaction sent: {tx_hash.hex()}")
print("Waiting for confirmation...")

# Wait for receipt
receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

if receipt.status == 1:
    print(f"✅ Schema registered successfully!")
    print(f"Gas used: {receipt.gasUsed}")
    
    # Try to decode the schema UID from logs
    if receipt.logs:
        # The schema UID is typically in the first log
        schema_uid = receipt.logs[0]['topics'][1] if len(receipt.logs[0]['topics']) > 1 else None
        if schema_uid:
            print(f"Schema UID: {schema_uid.hex()}")
        else:
            print("Schema UID: Check transaction logs for details")
else:
    print(f"❌ Transaction failed!")
    print(f"Receipt: {receipt}")