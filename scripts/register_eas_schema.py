#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "web3>=6.0.0",
#     "eth-account>=0.10.0",
# ]
# ///
"""
Register EAS Schema on Base Mainnet
"""

import os
import sys
from web3 import Web3
from eth_account import Account

# EAS Contract Address on Base Mainnet
EAS_CONTRACT_ADDRESS = "0x4200000000000000000000000000000000000021"

# EAS SchemaRegistry ABI (only the register function we need)
SCHEMA_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "schema", "type": "string"},
            {"internalType": "address", "name": "resolver", "type": "address"},
            {"internalType": "bool", "name": "revocable", "type": "bool"}
        ],
        "name": "register",
        "outputs": [
            {"internalType": "bytes32", "name": "", "type": "bytes32"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def register_schema():
    # Schema definition
    SCHEMA = "address agent, string spaceId, string proposalId, uint8 voteChoice, string snapshotSig, uint256 timestamp, string runId, uint8 confidence"
    
    # Get environment variables
    rpc_url = os.getenv("BASE_MAINNET_RPC_URL", "https://mainnet.base.org")
    private_key = os.getenv("PRIVATE_KEY")
    
    if not private_key:
        print("❌ Error: PRIVATE_KEY environment variable not set")
        print("Set it with: export PRIVATE_KEY=your_private_key_here")
        sys.exit(1)
    
    # Connect to Base mainnet
    print(f"🔗 Connecting to Base mainnet...")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print("❌ Failed to connect to Base mainnet")
        sys.exit(1)
    
    # Setup account
    account = Account.from_key(private_key)
    print(f"📝 Using account: {account.address}")
    
    # Check balance
    balance = w3.eth.get_balance(account.address)
    print(f"💰 Account balance: {Web3.from_wei(balance, 'ether')} ETH")
    
    if balance == 0:
        print("❌ Error: Account has no ETH for gas fees")
        sys.exit(1)
    
    # Get the SchemaRegistry contract
    # On Base, the SchemaRegistry is at a specific address
    # Base Mainnet SchemaRegistry: 0x4200000000000000000000000000000000000020
    SCHEMA_REGISTRY_ADDRESS = "0x4200000000000000000000000000000000000020"
    
    schema_registry = w3.eth.contract(
        address=SCHEMA_REGISTRY_ADDRESS,
        abi=SCHEMA_REGISTRY_ABI
    )
    
    print(f"\n📋 Registering schema:")
    print(f"   {SCHEMA}")
    print(f"   Revocable: True")
    print(f"   Resolver: 0x0000000000000000000000000000000000000000 (no resolver)")
    
    # Build the transaction
    try:
        # Estimate gas
        gas_estimate = schema_registry.functions.register(
            SCHEMA,
            "0x0000000000000000000000000000000000000000",  # No resolver
            True  # Revocable
        ).estimate_gas({'from': account.address})
        
        print(f"⛽ Estimated gas: {gas_estimate}")
        
        # Get current gas price
        gas_price = w3.eth.gas_price
        print(f"⛽ Gas price: {Web3.from_wei(gas_price, 'gwei')} gwei")
        
        # Build transaction
        tx = schema_registry.functions.register(
            SCHEMA,
            "0x0000000000000000000000000000000000000000",  # No resolver
            True  # Revocable
        ).build_transaction({
            'from': account.address,
            'gas': int(gas_estimate * 1.1),  # Add 10% buffer
            'gasPrice': gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': 8453  # Base mainnet chain ID
        })
        
        # Sign and send transaction
        print("\n🖊️  Signing transaction...")
        signed_tx = account.sign_transaction(tx)
        
        print("📤 Sending transaction...")
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"📝 Transaction hash: {tx_hash.hex()}")
        
        # Wait for confirmation
        print("⏳ Waiting for confirmation...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print("✅ Schema registered successfully!")
            
            # The schema UID is returned in the logs
            # Parse the logs to get the schema UID
            if receipt.logs:
                # The first log should contain the schema UID as the first topic
                schema_uid = receipt.logs[0]['topics'][0].hex() if receipt.logs[0]['topics'] else None
                if schema_uid:
                    print(f"\n🎉 Schema UID: {schema_uid}")
                    print(f"\n📌 Add this to your .env file:")
                    print(f"   EAS_SCHEMA_UID={schema_uid}")
                    
                    # Save to file for convenience
                    with open("schema_uid.txt", "w") as f:
                        f.write(f"EAS_SCHEMA_UID={schema_uid}\n")
                    print(f"\n💾 Schema UID saved to schema_uid.txt")
            
            print(f"\n🔗 View on BaseScan: https://basescan.org/tx/{tx_hash.hex()}")
            print(f"🔗 View on EAS: https://base.easscan.org/schema/view/{schema_uid if 'schema_uid' in locals() else 'check-transaction'}")
            
        else:
            print("❌ Transaction failed!")
            print(f"Receipt: {receipt}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    register_schema()