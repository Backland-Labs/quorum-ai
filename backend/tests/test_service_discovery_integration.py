# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "pytest>=8.4.1",
#     "web3>=7.12.0",
#     "eth-account>=0.13.7",
#     "requests>=2.32.4",
#     "pydantic>=2.10.0",
#     "pydantic-settings>=2.6.0",
#     "pydantic-ai",
#     "httpx>=0.28.0",
#     "python-dotenv>=1.0.0",
#     "safe-eth-py>=7.7.0",
#     "fastapi>=0.115.0",
#     "uvicorn[standard]>=0.32.0",
# ]
# ///

import sys
from pathlib import Path
import os

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Set environment variables BEFORE importing config to prevent RPC calls during init
os.environ.setdefault("SERVICE_ID", "1")

from web3 import Web3

# Correct ServiceRegistry address for Base
SERVICE_REGISTRY_ADDRESS = "0x3C1fF68f5aa342D296d4DEe4Bb1cACCA912D95fE"

def test_service_discovery_localhost_real():
    """
    Test service discovery against a real localhost RPC endpoint (anvil/fork).

    Note: The actual ServiceRegistry contract has a different structure than expected.
    It contains: serviceOwner, configHash, threshold, maxNumServices, numActiveInstances,
    serviceState, and agentIds - but NO multisig field.

    This test will query the actual contract to find services.
    """
    from web3 import Web3

    rpc_url = "http://localhost:8545"
    service_registry_address = SERVICE_REGISTRY_ADDRESS
    target_safe = "0x36Da714086a53F7658408D2e8a049a17eb4A90D5"

    # Real ABI based on the actual deployed contract
    REAL_SERVICE_REGISTRY_ABI = [
        {
            "name": "getService",
            "type": "function",
            "stateMutability": "view",
            "inputs": [{"name": "serviceId", "type": "uint256"}],
            "outputs": [
                {
                    "name": "service",
                    "type": "tuple",
                    "components": [
                        {"name": "securityDeposit", "type": "uint96"},
                        {"name": "multisig", "type": "address"},
                        {"name": "configHash", "type": "bytes32"},
                        {"name": "threshold", "type": "uint32"},
                        {"name": "maxNumAgentInstances", "type": "uint32"},
                        {"name": "numAgentInstances", "type": "uint32"},
                        {"name": "state", "type": "uint8"},
                        {"name": "agentIds", "type": "uint32[]"},
                    ],
                }
            ],
        },
        {
            "name": "totalSupply",
            "type": "function",
            "stateMutability": "view",
            "inputs": [],
            "outputs": [{"name": "", "type": "uint256"}],
        },
        {
            "name": "exists",
            "type": "function",
            "stateMutability": "view",
            "inputs": [{"name": "serviceId", "type": "uint256"}],
            "outputs": [{"name": "", "type": "bool"}],
        },
    ]

    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        print(f"Connected: {w3.is_connected()}")
        print(f"Chain ID: {w3.eth.chain_id}")

        contract = w3.eth.contract(
            address=service_registry_address,
            abi=REAL_SERVICE_REGISTRY_ABI,
        )

        print(f"\nSearching for Safe address: {target_safe}")
        print("=" * 80)

        # Search through services
        # Note: exists() may not be available, so we'll try getService() directly
        max_search = 200  # Contract has 190 services total
        last_checked = -1

        for service_id in range(max_search):
            try:
                service = contract.functions.getService(service_id).call()
                # Structure: (securityDeposit, multisig, configHash, threshold, maxNumAgentInstances, numAgentInstances, state, agentIds)
                security_deposit = service[0]
                multisig = service[1]
                config_hash = service[2]
                threshold = service[3]
                max_agents = service[4]
                num_agents = service[5]
                state = service[6]
                agent_ids = service[7]

                last_checked = service_id

                # Check if target matches the multisig address
                if multisig.lower() == target_safe.lower():
                    print(f"\n✓ FOUND!")
                    print(f"Service ID: {service_id}")
                    print(f"Multisig: {multisig}")
                    print(f"Security Deposit: {security_deposit}")
                    print(f"Threshold: {threshold}")
                    print(f"Max Agents: {max_agents} | Active: {num_agents}")
                    print(f"State: {state}")
                    print(f"Agent IDs: {agent_ids}")
                    return service_id

            except Exception as e:
                # If we get a revert, likely means no more services exist
                if service_id == 0:
                    print(f"Error on first service: {e}")
                    print("The contract may not have the expected interface")
                else:
                    print(f"\nReached end of services at ID {service_id}")
                break

        print(f"\n✗ Not found in services 0-{last_checked}")
        return None

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    print("=" * 80)
    print("Running ServiceDiscovery E2E integration test...")
    print("=" * 80)
    try:
        test_service_discovery_localhost_real()
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
