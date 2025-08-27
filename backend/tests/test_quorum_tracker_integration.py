"""Integration test for QuorumTracker smart contract."""

import os
from web3 import Web3
from eth_account import Account
import json


def test_quorum_tracker_integration():
    """Test basic interaction with the deployed QuorumTracker contract."""
    
    # Load environment variables
    contract_address = os.getenv("QUORUM_TRACKER_ADDRESS", "0x0451830c7f76ca89b52a4dbecf22f58a507282b9")
    owner_address = os.getenv("QUORUM_TRACKER_OWNER", "0x70997970C51812dc3A010C7d01b50e0d17dc79C8")
    private_key = os.getenv("QUORUM_TRACKER_PRIVATE_KEY", "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d")
    rpc_url = os.getenv("RPC_URL", "http://localhost:8545")
    
    # Connect to the network
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    assert w3.is_connected(), "Failed to connect to RPC"
    
    # Load the ABI
    abi = [
        {
            "inputs": [{"name": "multisig", "type": "address"}, {"name": "activityType", "type": "uint8"}],
            "name": "register",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [{"name": "multisig", "type": "address"}],
            "name": "getVotingStats",
            "outputs": [{"name": "", "type": "uint256[]"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "owner",
            "outputs": [{"name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "VOTES_CAST",
            "outputs": [{"name": "", "type": "uint8"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "OPPORTUNITIES_CONSIDERED",
            "outputs": [{"name": "", "type": "uint8"}],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [],
            "name": "NO_OPPORTUNITIES",
            "outputs": [{"name": "", "type": "uint8"}],
            "stateMutability": "view",
            "type": "function"
        }
    ]
    
    # Create contract instance (convert to checksum address)
    contract_address = w3.to_checksum_address(contract_address)
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    # Test 1: Verify contract owner
    print("Test 1: Verifying contract owner...")
    owner_address = w3.to_checksum_address(owner_address)
    actual_owner = contract.functions.owner().call()
    assert actual_owner == owner_address, f"Owner mismatch: {actual_owner} != {owner_address}"
    print(f"✓ Contract owner verified: {actual_owner}")
    
    # Test 2: Get activity type constants
    print("\nTest 2: Getting activity type constants...")
    votes_cast = contract.functions.VOTES_CAST().call()
    opportunities_considered = contract.functions.OPPORTUNITIES_CONSIDERED().call()
    no_opportunities = contract.functions.NO_OPPORTUNITIES().call()
    
    assert votes_cast == 0, f"VOTES_CAST should be 0, got {votes_cast}"
    assert opportunities_considered == 1, f"OPPORTUNITIES_CONSIDERED should be 1, got {opportunities_considered}"
    assert no_opportunities == 2, f"NO_OPPORTUNITIES should be 2, got {no_opportunities}"
    print(f"✓ Constants verified: VOTES_CAST={votes_cast}, OPPORTUNITIES_CONSIDERED={opportunities_considered}, NO_OPPORTUNITIES={no_opportunities}")
    
    # Test 3: Register an activity
    print("\nTest 3: Registering an activity...")
    test_multisig = "0x1234567890123456789012345678901234567890"
    
    # Get initial stats
    initial_stats = contract.functions.getVotingStats(test_multisig).call()
    print(f"Initial stats for {test_multisig}: {initial_stats}")
    
    # Prepare transaction
    account = Account.from_key(private_key)
    nonce = w3.eth.get_transaction_count(account.address)
    
    # Build transaction
    tx = contract.functions.register(test_multisig, votes_cast).build_transaction({
        'from': account.address,
        'nonce': nonce,
        'gas': 100000,
        'gasPrice': w3.to_wei('1', 'gwei'),
    })
    
    # Sign and send transaction
    signed_tx = account.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    # Wait for confirmation
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    assert receipt.status == 1, "Transaction failed"
    print(f"✓ Activity registered, tx hash: {tx_hash.hex()}")
    
    # Test 4: Verify stats were updated
    print("\nTest 4: Verifying stats were updated...")
    final_stats = contract.functions.getVotingStats(test_multisig).call()
    print(f"Final stats for {test_multisig}: {final_stats}")
    
    assert len(final_stats) == 3, f"Stats array should have 3 elements, got {len(final_stats)}"
    assert final_stats[0] == initial_stats[0] + 1, "Votes cast should be incremented by 1"
    assert final_stats[1] == initial_stats[1], "Opportunities considered should remain unchanged"
    assert final_stats[2] == initial_stats[2], "No opportunities should remain unchanged"
    print("✓ Stats correctly updated")
    
    print("\n✅ All integration tests passed!")
    return True


if __name__ == "__main__":
    test_quorum_tracker_integration()