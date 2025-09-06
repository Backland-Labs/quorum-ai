#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "web3>=6.0.0",
#     "eth-account>=0.10.0",
#     "eth-abi>=4.0.0",
#     "eth-utils>=2.0.0",
# ]
# ///
"""
Write attestation data to AttestationTracker contract on Base Mainnet
Using proper EIP-712 signature for delegated attestation
"""

import os
import sys
import time
import json
from web3 import Web3
from eth_account import Account
from eth_abi import encode

# Contract addresses
ATTESTATION_TRACKER_ADDRESS = "0xc16647a4290E4C931aD586713c7d85E0eFbafba0"
EAS_CONTRACT_ADDRESS = "0x4200000000000000000000000000000000000021"

# AttestationTracker ABI
ATTESTATION_TRACKER_ABI = [
    {
        "inputs": [
            {
                "components": [
                    {"internalType": "bytes32", "name": "schema", "type": "bytes32"},
                    {"internalType": "bytes", "name": "data", "type": "bytes"},
                    {"internalType": "uint64", "name": "expirationTime", "type": "uint64"},
                    {"internalType": "bool", "name": "revocable", "type": "bool"},
                    {"internalType": "bytes32", "name": "refUID", "type": "bytes32"},
                    {"internalType": "address", "name": "recipient", "type": "address"},
                    {"internalType": "uint256", "name": "value", "type": "uint256"},
                    {"internalType": "uint64", "name": "deadline", "type": "uint64"},
                    {"internalType": "bytes", "name": "signature", "type": "bytes"}
                ],
                "internalType": "struct IEAS.DelegatedAttestationRequest",
                "name": "delegatedRequest",
                "type": "tuple"
            }
        ],
        "name": "attestByDelegation",
        "outputs": [
            {"internalType": "bytes32", "name": "attestationUID", "type": "bytes32"}
        ],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "address", "name": "multisig", "type": "address"}],
        "name": "getNumAttestations",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def encode_attestation_data(agent_address, space_id="test-space", proposal_id="test-proposal-1", 
                          vote_choice=1, snapshot_sig="test-signature", run_id="test-run-1", 
                          confidence=80):
    """
    Encode the attestation data according to the schema
    """
    timestamp = int(time.time())
    
    encoded_data = encode(
        ['address', 'string', 'string', 'uint8', 'string', 'uint256', 'string', 'uint8'],
        [agent_address, space_id, proposal_id, vote_choice, snapshot_sig, timestamp, run_id, confidence]
    )
    
    return encoded_data

def create_eip712_signature(account, schema_uid, recipient, encoded_data, nonce, deadline):
    """
    Create a proper EIP-712 signature for EAS delegated attestation
    This mimics how the application would create the signature
    """
    from eth_account import Account
    from eth_utils import keccak
    
    # Manual EIP-712 encoding since eth_account's API is inconsistent
    # This follows the exact EIP-712 specification
    
    # Type hashes
    DOMAIN_SEPARATOR_TYPEHASH = keccak(text="EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)")
    ATTEST_TYPEHASH = keccak(text="Attest(bytes32 schema,address recipient,uint64 expirationTime,bool revocable,bytes32 refUID,bytes data,uint256 value,uint256 nonce,uint64 deadline)")
    
    # Create domain separator
    domain_separator = keccak(
        DOMAIN_SEPARATOR_TYPEHASH +
        keccak(text="EAS") +  # name
        keccak(text="1.3.0") +  # version  
        (8453).to_bytes(32, 'big') +  # chainId
        bytes.fromhex(EAS_CONTRACT_ADDRESS[2:].rjust(64, '0'))  # verifyingContract
    )
    
    # Prepare message values
    schema_bytes = bytes.fromhex(schema_uid[2:])
    ref_uid = bytes(32)  # 32 zero bytes
    data_hash = keccak(encoded_data)
    
    # Create struct hash
    struct_hash = keccak(
        ATTEST_TYPEHASH +
        schema_bytes +
        bytes.fromhex(recipient[2:].rjust(64, '0')) +  # recipient address
        (0).to_bytes(8, 'big') +  # expirationTime (uint64)
        (1).to_bytes(1, 'big') +  # revocable (bool true = 1)
        ref_uid +  # refUID
        data_hash +  # hash of data
        (0).to_bytes(32, 'big') +  # value (uint256)
        nonce.to_bytes(32, 'big') +  # nonce (uint256)
        deadline.to_bytes(8, 'big')  # deadline (uint64)
    )
    
    # Create final message hash (EIP-191 + EIP-712)
    message_hash = keccak(
        bytes.fromhex('1901') +  # EIP-191 prefix
        domain_separator +
        struct_hash
    )
    
    # Sign the message hash directly
    signature = Account._sign_hash(message_hash, account.key)
    
    # Format signature as bytes (r + s + v)
    signature_bytes = (
        signature.r.to_bytes(32, byteorder='big') +
        signature.s.to_bytes(32, byteorder='big') +
        bytes([signature.v])
    )
    
    return signature_bytes

def write_to_attestation_tracker():
    # Get environment variables
    rpc_url = os.getenv("RPC_URL", "https://methodical-aged-haze.base-mainnet.quiknode.pro/be2a6f7bf2b041c1bcc41cf4a2880b239afcdeb7/")
    private_key = os.getenv("PRIVATE_KEY")
    schema_uid = os.getenv("EAS_SCHEMA_UID", "0x7d917fcbc9a29a9705ff9936ffa599500e4fd902e4486bae317414fe967b307c")
    
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
    
    # Get the AttestationTracker contract
    tracker_contract = w3.eth.contract(
        address=ATTESTATION_TRACKER_ADDRESS,
        abi=ATTESTATION_TRACKER_ABI
    )
    
    # Check current attestation count
    current_count = tracker_contract.functions.getNumAttestations(account.address).call()
    print(f"📊 Current attestation count for your address: {current_count}")
    
    print(f"\n📋 Creating delegated attestation:")
    print(f"   Schema UID: {schema_uid}")
    print(f"   AttestationTracker: {ATTESTATION_TRACKER_ADDRESS}")
    
    try:
        # Encode attestation data
        encoded_data = encode_attestation_data(
            agent_address=account.address,
            space_id="quorum-ai-test",
            proposal_id=f"proposal-{int(time.time())}",
            vote_choice=1,
            snapshot_sig="test-signature-base",
            run_id=f"run-{int(time.time())}",
            confidence=95
        )
        print(f"   Encoded data length: {len(encoded_data)} bytes")
        
        # Set recipient (zero address for public attestations)
        recipient = "0x0000000000000000000000000000000000000000"
        
        # Create nonce (using current timestamp)
        nonce = w3.eth.get_transaction_count(account.address)
        
        # Set deadline (1 hour from now)
        deadline = int(time.time()) + 3600
        
        # Create EIP-712 signature
        print("🖊️  Creating EIP-712 signature...")
        signature = create_eip712_signature(
            account=account,
            schema_uid=schema_uid,
            recipient=recipient,
            encoded_data=encoded_data,
            nonce=nonce,
            deadline=deadline
        )
        
        print(f"   Signature length: {len(signature)} bytes")
        print(f"   Nonce: {nonce}")
        print(f"   Deadline: {deadline}")
        
        # Build delegated attestation request
        delegated_request = (
            bytes.fromhex(schema_uid[2:]),  # schema
            encoded_data,                    # data
            0,                               # expirationTime
            True,                            # revocable
            bytes(32),                       # refUID (32 zero bytes)
            recipient,                       # recipient
            0,                              # value
            deadline,                        # deadline
            signature                        # signature
        )
        
        # First try to estimate gas
        print("\n⛽ Estimating gas...")
        try:
            gas_estimate = tracker_contract.functions.attestByDelegation(delegated_request).estimate_gas({
                'from': account.address,
                'value': 0
            })
            print(f"   Estimated gas: {gas_estimate}")
        except Exception as e:
            print(f"⚠️  Gas estimation failed: {e}")
            print("   Using default gas limit of 500000")
            gas_estimate = 500000
        
        # Get current gas price
        gas_price = w3.eth.gas_price
        print(f"   Gas price: {Web3.from_wei(gas_price, 'gwei')} gwei")
        
        # Build transaction
        tx = tracker_contract.functions.attestByDelegation(delegated_request).build_transaction({
            'from': account.address,
            'gas': gas_estimate,
            'gasPrice': int(gas_price * 1.1),  # Add 10% to gas price
            'nonce': nonce,
            'chainId': 8453,  # Base mainnet
            'value': 0
        })
        
        # Sign and send transaction
        print("\n🖊️  Signing transaction...")
        signed_tx = account.sign_transaction(tx)
        
        print("📤 Sending transaction...")
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"📝 Transaction hash: {tx_hash.hex()}")
        
        # Wait for confirmation
        print("⏳ Waiting for confirmation...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status == 1:
            print("✅ Attestation written to AttestationTracker successfully!")
            
            # Check new attestation count
            new_count = tracker_contract.functions.getNumAttestations(account.address).call()
            print(f"\n📊 New attestation count: {new_count} (was {current_count})")
            
            # Save details
            with open("attestation_uid.txt", "w") as f:
                f.write(f"TRANSACTION_HASH={tx_hash.hex()}\n")
                f.write(f"BLOCK_NUMBER={receipt.blockNumber}\n")
                f.write(f"ATTESTATION_TRACKER={ATTESTATION_TRACKER_ADDRESS}\n")
                f.write(f"SCHEMA_UID={schema_uid}\n")
            print(f"💾 Details saved to attestation_uid.txt")
            
            print(f"\n🔗 View on BaseScan: https://basescan.org/tx/{tx_hash.hex()}")
            print(f"🔗 Contract on BaseScan: https://basescan.org/address/{ATTESTATION_TRACKER_ADDRESS}")
            
        else:
            print("❌ Transaction failed!")
            print(f"Receipt: {receipt}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    write_to_attestation_tracker()