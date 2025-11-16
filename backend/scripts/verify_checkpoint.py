#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "web3>=7.12.0",
#   "python-dotenv>=1.0.0",
#   "pydantic-settings>=2.6.0",
#   "pydantic>=2.10.0",
# ]
# ///
"""Verify checkpoint status on staking contract."""

import sys
from pathlib import Path
from web3 import Web3
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings

# Default staking contract address
STAKING_CONTRACT_ADDRESS = "0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb"

# ABI for reading checkpoint data
STAKING_ABI = [
    {
        "inputs": [{"type": "address"}],
        "name": "getStakingState",
        "outputs": [{"type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"type": "uint256"}],
        "name": "mapServiceInfo",
        "outputs": [
            {"name": "multisig", "type": "address"},
            {"name": "owner", "type": "address"},
            {"name": "stakingRewards", "type": "uint256"},
            {"name": "lastCheckpointTime", "type": "uint256"},
            {"name": "stakingTime", "type": "uint256"},
            {"name": "state", "type": "uint8"},
            {"name": "serviceIds", "type": "uint256[]"}
        ],
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
        "name": "maxAllowedInactivity",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "checkpointLength",
        "outputs": [{"type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def main():
    """Check checkpoint status on staking contract."""

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
    print(f"\nCurrent block time: {current_time} (timestamp: {current_timestamp})")

    # Initialize contract
    contract_address = getattr(settings, 'staking_contract_address', None) or STAKING_CONTRACT_ADDRESS
    contract = w3.eth.contract(
        address=contract_address,
        abi=STAKING_ABI
    )

    print(f"\nQuerying staking contract: {contract_address}")

    try:
        # Get liveness period and max inactivity
        liveness_period = contract.functions.livenessPeriod().call()
        max_inactivity = contract.functions.maxAllowedInactivity().call()
        checkpoint_length = contract.functions.checkpointLength().call()

        print(f"\nContract parameters:")
        print(f"  Liveness period: {liveness_period} seconds ({liveness_period / 3600:.1f} hours)")
        print(f"  Max allowed inactivity: {max_inactivity} seconds ({max_inactivity / 3600:.1f} hours)")
        print(f"  Checkpoint length: {checkpoint_length}")

        # Try to get service info for a known service ID
        # You might need to adjust the service ID based on your deployment
        service_ids = [1, 2, 3, 4, 5]  # Try multiple IDs

        print(f"\nChecking service info:")
        found_service = False

        for service_id in service_ids:
            try:
                info = contract.functions.mapServiceInfo(service_id).call()
                if info[0] != '0x0000000000000000000000000000000000000000':  # Has multisig
                    found_service = True
                    multisig = info[0]
                    owner = info[1]
                    rewards = info[2]
                    last_checkpoint = info[3]
                    staking_time = info[4]
                    state = info[5]

                    print(f"\nService ID {service_id}:")
                    print(f"  Multisig: {multisig}")
                    print(f"  Owner: {owner}")
                    print(f"  Staking rewards: {rewards}")
                    print(f"  Last checkpoint: {datetime.fromtimestamp(last_checkpoint) if last_checkpoint > 0 else 'Never'}")
                    print(f"  Last checkpoint timestamp: {last_checkpoint}")
                    print(f"  Staking time: {datetime.fromtimestamp(staking_time) if staking_time > 0 else 'Not staked'}")
                    print(f"  State: {state} (0=Unstaked, 1=Staked, 2=Evicted)")

                    if last_checkpoint > 0:
                        time_since_checkpoint = current_timestamp - last_checkpoint
                        next_checkpoint_due = last_checkpoint + liveness_period
                        next_checkpoint_time = datetime.fromtimestamp(next_checkpoint_due)
                        time_until_next = next_checkpoint_due - current_timestamp

                        print(f"\nCheckpoint timing:")
                        print(f"  Time since last checkpoint: {time_since_checkpoint} seconds ({time_since_checkpoint / 3600:.1f} hours)")
                        print(f"  Next checkpoint due: {next_checkpoint_time}")
                        print(f"  Next checkpoint timestamp: {next_checkpoint_due}")

                        if time_until_next > 0:
                            print(f"  Time until next checkpoint: {time_until_next} seconds ({time_until_next / 3600:.1f} hours)")
                            print(f"  Status: ✅ NOT OVERDUE")
                        else:
                            overdue_by = abs(time_until_next)
                            print(f"  OVERDUE by: {overdue_by} seconds ({overdue_by / 3600:.1f} hours)")
                            print(f"  Status: ⚠️ OVERDUE")

                        # Check if at risk of eviction
                        if time_since_checkpoint > max_inactivity:
                            print(f"  ⚠️ WARNING: Service at risk of eviction (exceeded max inactivity)")

            except Exception as e:
                # Service ID doesn't exist, continue
                continue

        if not found_service:
            print("\nNo staked services found in checked range")
            print("You may need to check your service ID or stake a service first")

            # Try to check if our safe address has a service
            safe_addresses = settings.safe_contract_addresses
            if safe_addresses:
                import json
                addresses = json.loads(safe_addresses)
                for chain, address in addresses.items():
                    print(f"\nChecking safe {address} on {chain}...")
                    try:
                        state = contract.functions.getStakingState(address).call()
                        print(f"  Staking state for safe: {state} (0=Unstaked, 1=Staked, 2=Evicted)")
                    except Exception as e:
                        print(f"  Could not query staking state: {e}")

    except Exception as e:
        print(f"\nError querying contract: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()