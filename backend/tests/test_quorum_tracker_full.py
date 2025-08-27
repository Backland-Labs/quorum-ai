"""Comprehensive integration test for QuorumTracker smart contract."""

import os
from web3 import Web3
from eth_account import Account


def test_quorum_tracker_full():
    """Test all activity types with the deployed QuorumTracker contract."""
    
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
    
    # Create contract instance
    contract_address = w3.to_checksum_address(contract_address)
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    # Get constants
    VOTES_CAST = contract.functions.VOTES_CAST().call()
    OPPORTUNITIES_CONSIDERED = contract.functions.OPPORTUNITIES_CONSIDERED().call()
    NO_OPPORTUNITIES = contract.functions.NO_OPPORTUNITIES().call()
    
    # Test multisig addresses
    test_multisigs = [
        "0xAAA0000000000000000000000000000000000001",
        "0xBBB0000000000000000000000000000000000002",
        "0xCCC0000000000000000000000000000000000003"
    ]
    
    account = Account.from_key(private_key)
    
    print("Testing QuorumTracker with multiple activity types and multisigs...")
    print("=" * 60)
    
    for i, multisig in enumerate(test_multisigs):
        multisig = w3.to_checksum_address(multisig)
        print(f"\n📊 Testing multisig {i+1}: {multisig}")
        
        # Get initial stats
        initial_stats = contract.functions.getVotingStats(multisig).call()
        print(f"  Initial stats: Votes={initial_stats[0]}, Opportunities={initial_stats[1]}, NoOps={initial_stats[2]}")
        
        # Register different activities based on multisig index
        activity_types = [
            (VOTES_CAST, "VOTES_CAST"),
            (OPPORTUNITIES_CONSIDERED, "OPPORTUNITIES_CONSIDERED"),
            (NO_OPPORTUNITIES, "NO_OPPORTUNITIES")
        ]
        
        activity_type, activity_name = activity_types[i]
        
        # Register activity
        nonce = w3.eth.get_transaction_count(account.address)
        tx = contract.functions.register(multisig, activity_type).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': w3.to_wei('1', 'gwei'),
        })
        
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        assert receipt.status == 1, f"Transaction failed for {multisig}"
        print(f"  ✓ Registered activity: {activity_name}")
        print(f"    Transaction: {tx_hash.hex()[:16]}...")
        
        # Verify stats
        final_stats = contract.functions.getVotingStats(multisig).call()
        print(f"  Final stats: Votes={final_stats[0]}, Opportunities={final_stats[1]}, NoOps={final_stats[2]}")
        
        # Validate the correct counter was incremented
        expected_index = activity_type
        for idx in range(3):
            if idx == expected_index:
                assert final_stats[idx] == initial_stats[idx] + 1, f"Counter {idx} should be incremented"
            else:
                assert final_stats[idx] == initial_stats[idx], f"Counter {idx} should remain unchanged"
        
        print(f"  ✅ Verification passed!")
    
    # Test multiple activities for same multisig
    print(f"\n📈 Testing multiple activities for same multisig...")
    multi_test_multisig = w3.to_checksum_address("0xDDD0000000000000000000000000000000000004")
    
    for activity_type, activity_name in activity_types:
        nonce = w3.eth.get_transaction_count(account.address)
        tx = contract.functions.register(multi_test_multisig, activity_type).build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': w3.to_wei('1', 'gwei'),
        })
        
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        assert receipt.status == 1
        print(f"  ✓ Registered {activity_name}")
    
    # Final verification
    final_stats = contract.functions.getVotingStats(multi_test_multisig).call()
    assert final_stats[0] == 1, "Should have 1 vote cast"
    assert final_stats[1] == 1, "Should have 1 opportunity considered"
    assert final_stats[2] == 1, "Should have 1 no opportunity"
    print(f"  Final combined stats: Votes={final_stats[0]}, Opportunities={final_stats[1]}, NoOps={final_stats[2]}")
    
    print("\n" + "=" * 60)
    print("🎉 All comprehensive tests passed successfully!")
    print(f"✅ Contract Address: {contract_address}")
    print(f"✅ Owner Address: {w3.to_checksum_address(owner_address)}")
    print(f"✅ Total test transactions: 6")
    return True


if __name__ == "__main__":
    test_quorum_tracker_full()