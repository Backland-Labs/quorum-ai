#!/usr/bin/env python3
"""Test EAS attestation directly without Safe infrastructure."""

import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

import asyncio
from web3 import Web3
from eth_account import Account
from models import EASAttestationData
import time


async def test_direct_eas_attestation():
    """Test EAS attestation by calling the contract directly."""
    
    print("=" * 60)
    print("Testing Direct EAS Attestation")
    print("=" * 60)
    
    # Connect to local Anvil
    w3 = Web3(Web3.HTTPProvider("http://localhost:8545"))
    
    # Load private key and account
    private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    account = Account.from_key(private_key)
    
    # Contract addresses
    attestation_tracker = "0x82372200341a23377129Ccc1aE2EFeB3048440eC"
    schema_uid = "0x4b646acb1d459357d3be21287c81da4026e8440b7283efbab2d124c54478b429"
    
    print(f"\nConfiguration:")
    print(f"  Account: {account.address}")
    print(f"  Balance: {w3.eth.get_balance(account.address) / 10**18:.4f} ETH")
    print(f"  AttestationTracker: {attestation_tracker}")
    print(f"  Schema UID: {schema_uid}")
    
    # Create test attestation data
    test_data = EASAttestationData(
        voter_address=account.address,
        proposal_id="0x123test",
        space_id="test-space.eth",
        choice=1,
        vote_tx_hash="0x" + "0" * 64,
        timestamp=int(time.time()),
        attestation_uid="",
        attestation_tx_hash="0x" + "0" * 64
    )
    
    # Import SafeService to use its signing methods
    from services.safe_service import SafeService
    safe_service = SafeService()
    
    # Build the transaction data using SafeService methods
    tx_data = safe_service._build_eas_attestation_tx(test_data)
    
    print(f"\nTransaction Data:")
    print(f"  To: {tx_data['to']}")
    print(f"  Data length: {len(tx_data['data'])} bytes")
    print(f"  Data preview: {tx_data['data'][:100]}...")
    
    # Send transaction directly
    try:
        print(f"\nSending transaction...")
        
        # Build transaction
        tx = {
            'from': account.address,
            'to': Web3.to_checksum_address(tx_data['to']),
            'data': tx_data['data'],
            'value': tx_data.get('value', 0),
            'gas': 500000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'chainId': 8453  # Base chain ID
        }
        
        # Sign and send
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"✅ Transaction sent: {tx_hash.hex()}")
        print("Waiting for confirmation...")
        
        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt.status == 1:
            print(f"✅ SUCCESS! Attestation created on-chain")
            print(f"  Gas used: {receipt.gasUsed}")
            print(f"  Block: {receipt.blockNumber}")
            
            # Check if there are logs (attestation events)
            if receipt.logs:
                print(f"  Events emitted: {len(receipt.logs)}")
                for i, log in enumerate(receipt.logs):
                    print(f"    Event {i+1}: {log.address[:10]}... topics={len(log.topics)}")
        else:
            print(f"❌ Transaction FAILED!")
            print(f"  Status: {receipt.status}")
            
    except Exception as e:
        print(f"❌ Error sending transaction: {e}")
        
        # Try to get more details
        if "execution reverted" in str(e):
            print("\n⚠️  Transaction would revert. Checking why...")
            
            # Try calling the function to get revert reason
            try:
                result = w3.eth.call({
                    'to': Web3.to_checksum_address(tx_data['to']),
                    'data': tx_data['data']
                })
                print(f"Unexpected success: {result.hex()}")
            except Exception as call_error:
                print(f"Revert reason: {call_error}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(test_direct_eas_attestation())