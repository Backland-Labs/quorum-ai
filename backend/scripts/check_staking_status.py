#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "web3>=7.12.0",
#   "python-dotenv>=1.0.0",
#   "pydantic-settings>=2.6.0",
#   "pydantic>=2.10.0",
# ]
# ///
"""Check staking status directly from contract."""

import sys
import json
from pathlib import Path
from web3 import Web3
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings

# Default staking contract address
STAKING_CONTRACT_ADDRESS = "0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb"

# ABI for ServiceStaking contract
STAKING_ABI = json.loads("""[
    {
        "inputs": [],
        "name": "getNextRewardCheckpointTimestamp",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "livenessPeriod",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "tsCheckpoint",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]""")

def main():
    """Check staking checkpoint status."""

    # Setup Web3
    rpc_url = settings.base_ledger_rpc
    if not rpc_url:
        print("Error: BASE_LEDGER_RPC not configured")
        sys.exit(1)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        print(f"Error: Cannot connect to RPC: {rpc_url}")
        sys.exit(1)

    print(f"Connected to chain_id={w3.eth.chain_id}")

    # Get current block timestamp
    current_block = w3.eth.get_block('latest')
    current_timestamp = current_block['timestamp']
    current_time = datetime.fromtimestamp(current_timestamp)
    print(f"\nCurrent block time: {current_time}")
    print(f"Current timestamp: {current_timestamp}")

    # Initialize contract
    contract_address = getattr(settings, 'staking_contract_address', None) or STAKING_CONTRACT_ADDRESS
    contract = w3.eth.contract(
        address=contract_address,
        abi=STAKING_ABI
    )

    print(f"\nQuerying staking contract: {contract_address}")

    try:
        # Get last checkpoint timestamp
        last_checkpoint = contract.functions.tsCheckpoint().call()
        last_checkpoint_time = datetime.fromtimestamp(last_checkpoint) if last_checkpoint > 0 else None

        print(f"\nLast checkpoint:")
        print(f"  Time: {last_checkpoint_time if last_checkpoint_time else 'Never'}")
        print(f"  Timestamp: {last_checkpoint}")

        # Get liveness period
        liveness_period = contract.functions.livenessPeriod().call()
        print(f"\nLiveness period: {liveness_period} seconds ({liveness_period / 3600:.1f} hours)")

        # Get next checkpoint timestamp
        next_checkpoint = contract.functions.getNextRewardCheckpointTimestamp().call()
        next_checkpoint_time = datetime.fromtimestamp(next_checkpoint) if next_checkpoint > 0 else None

        print(f"\nNext checkpoint due:")
        print(f"  Time: {next_checkpoint_time if next_checkpoint_time else 'Not scheduled'}")
        print(f"  Timestamp: {next_checkpoint}")

        if next_checkpoint > 0:
            time_until_next = next_checkpoint - current_timestamp

            if time_until_next > 0:
                hours = time_until_next / 3600
                minutes = (time_until_next % 3600) / 60
                print(f"\nTime until next checkpoint: {int(hours)} hours, {int(minutes)} minutes")
                print(f"Status: ✅ NOT OVERDUE")
            else:
                overdue_by = abs(time_until_next)
                hours = overdue_by / 3600
                minutes = (overdue_by % 3600) / 60
                print(f"\n⚠️ OVERDUE by: {int(hours)} hours, {int(minutes)} minutes")
                print(f"Status: ⚠️ CHECKPOINT OVERDUE")
        else:
            print(f"\nNo next checkpoint scheduled")

    except Exception as e:
        print(f"\nError querying contract: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()