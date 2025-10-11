#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "eth-account>=0.13.7",
#   "web3>=7.12.0",
#   "safe-eth-py>=7.7.0",
#   "python-dotenv>=1.0.0",
# ]
# ///
"""
Minimal Safe transaction test script.
Usage: SAFE_ADDRESS=0x... PRIVATE_KEY=0x... RPC_URL=https://... ./scripts/test_safe_simple.py
"""

import os
import sys
from eth_account import Account
from safe_eth.safe import Safe
from safe_eth.eth import EthereumClient


def main():
    # Get environment variables
    safe_address = ""
    rpc_url = os.getenv("RPC_URL", "https://cosmopolitan-cosmological-resonance.base-mainnet.quiknode.pro/b4c827323f0a8012212429b0bd4a72a060c5373c/")
    
    if not safe_address or not private_key:
        print("❌ Missing required environment variables:")
        print("   SAFE_ADDRESS=0x...")
        print("   PRIVATE_KEY=0x...")
        print("   RPC_URL=https://... (optional, defaults to Base mainnet)")
        sys.exit(1)
    
    print("=" * 80)
    print("SAFE TRANSACTION TEST")
    print("=" * 80)
    print(f"Safe: {safe_address}")
    print(f"RPC: {rpc_url}")
    
    # Setup
    account = Account.from_key(private_key)
    print(f"Signer: {account.address}")
    
    ethereum_client = EthereumClient(rpc_url)
    safe = Safe(safe_address, ethereum_client)
    
    # Get transaction details from environment or use defaults
    to_address = os.getenv("TO_ADDRESS", account.address)
    value = int(os.getenv("VALUE", "0"))
    data = os.getenv("DATA", "0x")
    
    print(f"\nTransaction:")
    print(f"  To: {to_address}")
    print(f"  Value: {value}")
    print(f"  Data: {data}")
    
    # Build Safe transaction
    print("\n" + "-" * 80)
    print("Building Safe transaction...")
    print("-" * 80)
    
    safe_tx = safe.build_multisig_tx(
        to=to_address,
        value=value,
        data=bytes.fromhex(data.replace("0x", "")),
    )
    
    print(f"✓ Built Safe TX (nonce={safe_tx.safe_nonce}, hash={safe_tx.safe_tx_hash.hex()})")
    
    # Sign transaction
    print("\n" + "-" * 80)
    print("Signing transaction...")
    print("-" * 80)
    
    safe_tx.sign(private_key)
    print(f"✓ Signed with {account.address}")
    
    # Simulate transaction
    print("\n" + "-" * 80)
    print("Simulating transaction...")
    print("-" * 80)
    
    # First test WITHOUT tx_sender_address (should fail)
    print("\n[TEST 1] Calling safe_tx.call() WITHOUT tx_sender_address:")
    try:
        safe_tx.call()
        print("✓ Simulation successful")
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        print(f"   Error type: {type(e).__name__}")
    
    # Second test WITH tx_sender_address (should succeed)
    print("\n[TEST 2] Calling safe_tx.call(tx_sender_address=account.address):")
    try:
        safe_tx.call(tx_sender_address=account.address)
        print("✓ Simulation successful")
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        print(f"   Error type: {type(e).__name__}")
        sys.exit(1)
    
    # Execute transaction
    print("\n" + "-" * 80)
    print("Executing transaction on-chain...")
    print("-" * 80)
    
    ethereum_tx = safe.send_multisig_tx(
        to=safe_tx.to,
        value=safe_tx.value,
        data=safe_tx.data,
        operation=safe_tx.operation,
        safe_tx_gas=safe_tx.safe_tx_gas,
        base_gas=safe_tx.base_gas,
        gas_price=safe_tx.gas_price,
        gas_token=safe_tx.gas_token,
        refund_receiver=safe_tx.refund_receiver,
        signatures=safe_tx.signatures,
        tx_sender_private_key=private_key,
    )
    
    tx_hash = ethereum_tx.tx_hash
    
    print(f"✓ Executed! TX hash: {tx_hash.hex()}")
    
    # Wait for confirmation
    w3 = ethereum_client.w3
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt["status"] == 1:
        print(f"✓ Confirmed in block {receipt['blockNumber']}")
    else:
        print(f"❌ Transaction reverted")
        sys.exit(1)


if __name__ == "__main__":
    main()
