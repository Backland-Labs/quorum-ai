#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "eth-account>=0.13.7",
#   "web3>=7.12.0",
#   "httpx>=0.28.0",
#   "pydantic>=2.10.0",
#   "pydantic-settings>=2.6.0",
#   "pydantic-ai",
#   "safe-eth-py>=7.7.0",
#   "fastapi>=0.115.0",
#   "python-dotenv>=1.0.0",
# ]
# ///
"""
Test script for debugging Safe transaction simulation issues.
Usage: ./scripts/test_safe_transaction.py
"""

import asyncio
import sys
from pathlib import Path
from eth_account import Account
from eth_account.messages import encode_defunct

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from services.safe_service import SafeService
from config import settings


async def test_eas_attestation():
    """Test EAS attestation through Safe to identify revert reasons."""
    
    print("=" * 80)
    print("SAFE TRANSACTION SIMULATION TEST")
    print("=" * 80)
    
    # Initialize services
    safe_service = SafeService()
    
    # Real data from logs
    proposal_id = "0xf963e0ad37b2f584b8221d6b0ff2d253196ed73b1a67129f0a617ea8922327ba"
    space_id = "quorum-ai.eth"
    vote_choice = 1
    attestation_tracker = "0x9BC8c713a159a028aC5590ffE42DaF0d9A6467AC"
    safe_address = "0x7dF2A42C5a9006B16E6c7e6Ac750cdf336489c80"
    agent_address = "0xA1F3Cd3668632FE656f156313d6C91562EDdC4A7"
    chain = "base"
    
    print(f"\nConfiguration:")
    print(f"  Chain: {chain}")
    print(f"  Safe: {safe_address}")
    print(f"  Agent: {agent_address}")
    print(f"  Attestation Tracker: {attestation_tracker}")
    print(f"  Proposal: {proposal_id}")
    print(f"  Vote Choice: {vote_choice}")
    
    try:
        print("\n" + "-" * 80)
        print("Step 1: Creating EAS attestation transaction data")
        print("-" * 80)
        
        # Create the attestation data (same as in agent run)
        eas_data = {
            "proposal_id": proposal_id,
            "space_id": space_id,
            "vote_choice": vote_choice,
            "agent_address": agent_address,
        }
        
        tx_data = await safe_service.create_eas_attestation(eas_data)
        
        print(f"✓ Transaction built:")
        print(f"  To: {tx_data['to']}")
        print(f"  Data length: {len(tx_data['data'])} bytes")
        print(f"  Value: {tx_data['value']}")
        
        print("\n" + "-" * 80)
        print("Step 2: Simulating Safe transaction")
        print("-" * 80)
        
        # This will trigger the simulation with improved error logging
        result = await safe_service._submit_safe_transaction(
            to_address=tx_data["to"],
            data=tx_data["data"],
            value=tx_data["value"],
            chain=chain,
        )
        
        print("\n" + "=" * 80)
        print("✅ SIMULATION SUCCESSFUL")
        print("=" * 80)
        print(f"Result: {result}")
        
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ SIMULATION FAILED")
        print("=" * 80)
        print(f"Error: {e}")
        print(f"Error Type: {type(e).__name__}")
        
        if hasattr(e, 'args'):
            print(f"Error Args: {e.args}")
        
        import traceback
        print("\nFull Traceback:")
        traceback.print_exc()
        
    finally:
        await safe_service.close()


async def test_simple_transaction():
    """Test a simple Safe transaction to verify basic functionality."""
    
    print("\n" + "=" * 80)
    print("SIMPLE SAFE TRANSACTION TEST")
    print("=" * 80)
    
    safe_service = SafeService()
    
    # Simple ETH transfer (should succeed if Safe has funds)
    try:
        result = await safe_service._submit_safe_transaction(
            to_address="0xA1F3Cd3668632FE656f156313d6C91562EDdC4A7",  # Agent address
            data="0x",  # Empty data for simple transfer
            value=0,  # 0 ETH
            chain="base",
        )
        
        print(f"✅ Simple transaction result: {result}")
        
    except Exception as e:
        print(f"❌ Simple transaction failed: {e}")
        
    finally:
        await safe_service.close()


async def main():
    """Run all tests."""
    
    # Test 1: Full EAS attestation flow
    await test_eas_attestation()
    
    # Test 2: Simple transaction
    print("\n" * 2)
    await test_simple_transaction()


if __name__ == "__main__":
    asyncio.run(main())
