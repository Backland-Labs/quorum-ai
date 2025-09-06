#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "web3>=6.0.0",
#     "eth-account>=0.10.0",
#     "eth-abi>=5.0.0",
# ]
# ///
"""
Register EAS Attestation on Base Mainnet
"""

import os
import sys
from web3 import Web3
from eth_account import Account

# EAS Contract Address on Base Mainnet
EAS_CONTRACT_ADDRESS = "0x4200000000000000000000000000000000000021"

# EAS Contract ABI (only the attest function we need)
EAS_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "bytes32", "name": "schema", "type": "bytes32"},
                    {
                        "components": [
                            {"internalType": "address", "name": "recipient", "type": "address"},
                            {"internalType": "uint64", "name": "expirationTime", "type": "uint64"},
                            {"internalType": "bool", "name": "revocable", "type": "bool"},
                            {"internalType": "bytes32", "name": "refUID", "type": "bytes32"},
                            {"internalType": "bytes", "name": "data", "type": "bytes"},
                            {"internalType": "uint256", "name": "value", "type": "uint256"}
                        ],
                        "internalType": "struct AttestationRequestData",
                        "name": "data",
                        "type": "tuple"
                    }
                ],
                "internalType": "struct AttestationRequest",
                "name": "request",
                "type": "tuple"
            }
        ],
        "name": "attest",
        "outputs": [
            {"internalType": "bytes32", "name": "", "type": "bytes32"}
        ],
        "stateMutability": "payable",
        "type": "function"
    }
]

def encode_attestation_data():
    """
    Encode the attestation data according to the schema:
    address agent, string spaceId, string proposalId, uint8 voteChoice, 
    string snapshotSig, uint256 timestamp, string runId, uint8 confidence
    """
    # For this example, we'll use empty/zero values
    # In practice, these would be provided as parameters
    agent = "0x0000000000000000000000000000000000000000"
    space_id = ""
    proposal_id = ""
    vote_choice = 0
    snapshot_sig = ""
    timestamp = 0
    run_id = ""
    confidence = 0
    
    # Encode the data using eth_abi
    from eth_abi import encode
    
    encoded_data = encode(
        ['address', 'string', 'string', 'uint8', 'string', 'uint256', 'string', 'uint8'],
        [agent, space_id, proposal_id, vote_choice, snapshot_sig, timestamp, run_id, confidence]
    )
    
    return encoded_data

def register_attestation():
    # Get environment variables
    rpc_url = os.getenv("BASE_MAINNET_RPC_URL", "https://methodical-aged-haze.base-mainnet.quiknode.pro/be2a6f7bf2b041c1bcc41cf4a2880b239afcdeb7/")
    private_key = os.getenv("PRIVATE_KEY")
    schema_uid = os.getenv("EAS_SCHEMA_UID", "0xc93c2cd5d2027a300cc7ca3d22b36b5581353f6dabab6e14eb41daf76d5b0eb4")
    
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
    
    # Get the EAS contract
    eas_contract = w3.eth.contract(
        address=EAS_CONTRACT_ADDRESS,
        abi=EAS_ABI
    )
    
    print(f"\n📋 Creating attestation:")
    print(f"   Schema UID: {schema_uid}")
    print(f"   Recipient: 0x0000000000000000000000000000000000000000")
    print(f"   Revocable: True")
    
    # Encode attestation data
    try:
        encoded_data = encode_attestation_data()
        print(f"   Encoded data length: {len(encoded_data)} bytes")
        
        # Build attestation request
        attestation_request = {
            'schema': bytes.fromhex(schema_uid[2:]),  # Remove 0x prefix
            'data': {
                'recipient': "0x0000000000000000000000000000000000000000",
                'expirationTime': 0,  # No expiration
                'revocable': True,
                'refUID': b'\x00' * 32,  # No reference
                'data': encoded_data,
                'value': 0  # No ETH value
            }
        }
        
        # Estimate gas
        gas_estimate = eas_contract.functions.attest(attestation_request).estimate_gas({
            'from': account.address
        })
        
        print(f"⛽ Estimated gas: {gas_estimate}")
        
        # Get current gas price
        gas_price = w3.eth.gas_price
        print(f"⛽ Gas price: {Web3.from_wei(gas_price, 'gwei')} gwei")
        
        # Build transaction
        tx = eas_contract.functions.attest(attestation_request).build_transaction({
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
            print("✅ Attestation created successfully!")
            
            # The attestation UID is the return value of the function
            # Parse the logs to get the attestation UID
            if receipt.logs:
                # The attestation UID is typically in the first log's first topic
                attestation_uid = receipt.logs[0]['topics'][1].hex() if len(receipt.logs[0]['topics']) > 1 else None
                if attestation_uid:
                    print(f"\n🎉 Attestation UID: {attestation_uid}")
                    
                    # Save to file for convenience
                    with open("attestation_uid.txt", "w") as f:
                        f.write(f"ATTESTATION_UID={attestation_uid}\n")
                    print(f"\n💾 Attestation UID saved to attestation_uid.txt")
            
            print(f"\n🔗 View on BaseScan: https://basescan.org/tx/{tx_hash.hex()}")
            print(f"🔗 View on EAS: https://base.easscan.org/attestation/view/{attestation_uid if 'attestation_uid' in locals() else 'check-transaction'}")
            
        else:
            print("❌ Transaction failed!")
            print(f"Receipt: {receipt}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    register_attestation()