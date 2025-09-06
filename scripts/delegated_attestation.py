#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "web3>=6.0.0",
#     "eth-account>=0.10.0",
#     "eth-abi>=5.0.0",
#     "eth-utils>=2.0.0",
# ]
# ///
"""
Create a delegated attestation for AttestationTracker on Base Mainnet.

This script matches the JavaScript SDK example for attestByDelegation:
- Creates EIP-712 signature using signDelegatedAttestation format
- Properly structures the nested AttestationRequestData tuple
- Includes v, r, s signature components separately
- Passes attester address explicitly
- Compatible with @ethereum-attestation-service/eas-sdk
"""

import os
import sys
import time
import json
from web3 import Web3
from eth_account import Account
from eth_abi.abi import encode

# Constants matching EAS SDK
NO_EXPIRATION = 0  # Used for attestation expiration and deadline

# Contract addresses
ATTESTATION_TRACKER_ADDRESS = "0xc16647a4290E4C931aD586713c7d85E0eFbafba0"
EAS_CONTRACT_ADDRESS = "0x4200000000000000000000000000000000000021"

# AttestationTracker ABI - matching EAS contract structure
ATTESTATION_TRACKER_ABI = [
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
                    },
                    {
                        "components": [
                            {"internalType": "uint8", "name": "v", "type": "uint8"},
                            {"internalType": "bytes32", "name": "r", "type": "bytes32"},
                            {"internalType": "bytes32", "name": "s", "type": "bytes32"}
                        ],
                        "internalType": "struct Signature",
                        "name": "signature",
                        "type": "tuple"
                    },
                    {"internalType": "address", "name": "attester", "type": "address"},
                    {"internalType": "uint64", "name": "deadline", "type": "uint64"}
                ],
                "internalType": "struct DelegatedAttestationRequest",
                "name": "delegatedRequest",
                "type": "tuple"
            }
        ],
        "name": "attestByDelegation",
        "outputs": [
            {"internalType": "bytes32", "name": "", "type": "bytes32"}
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

def encode_attestation_data(agent_address, space_id="test-space", proposal_id="test-proposal", 
                          vote_choice=1, snapshot_sig="sig", run_id="run-1", confidence=80):
    """
    Encode the attestation data according to the schema
    """
    timestamp = int(time.time())
    
    encoded_data = encode(
        ['address', 'string', 'string', 'uint8', 'string', 'uint256', 'string', 'uint8'],
        [agent_address, space_id, proposal_id, vote_choice, snapshot_sig, timestamp, run_id, confidence]
    )
    
    return encoded_data

def create_delegated_attestation_signature(w3, account, schema_uid, recipient, encoded_data, nonce, deadline):
    """
    Create EIP-712 signature for EAS delegated attestation.
    Matches the JavaScript SDK's signDelegatedAttestation format.
    """
    from eth_account.messages import encode_typed_data
    
    print(f"\n🔐 Creating EIP-712 signature with:")
    print(f"   Schema UID: {schema_uid}")
    print(f"   Recipient: {recipient}")
    print(f"   Nonce: {nonce}")
    print(f"   Deadline: {deadline}")
    print(f"   Chain ID: {w3.eth.chain_id}")
    
    # EAS EIP-712 domain and types structure (matching JS SDK)
    types = {
        'EIP712Domain': [
            {'name': 'name', 'type': 'string'},
            {'name': 'version', 'type': 'string'},
            {'name': 'chainId', 'type': 'uint256'},
            {'name': 'verifyingContract', 'type': 'address'},
        ],
        'Attest': [
            {'name': 'schema', 'type': 'bytes32'},
            {'name': 'recipient', 'type': 'address'},
            {'name': 'expirationTime', 'type': 'uint64'},
            {'name': 'revocable', 'type': 'bool'},
            {'name': 'refUID', 'type': 'bytes32'},
            {'name': 'data', 'type': 'bytes'},
            {'name': 'value', 'type': 'uint256'},
            {'name': 'nonce', 'type': 'uint256'},
            {'name': 'deadline', 'type': 'uint64'},
        ]
    }
    
    # EAS domain for Base mainnet
    domain = {
        'name': 'EAS',
        'version': '1.0.1',  # EAS contract version on Base
        'chainId': w3.eth.chain_id,
        'verifyingContract': Web3.to_checksum_address(EAS_CONTRACT_ADDRESS),
    }
    
    # Message data matching JS SDK structure
    message = {
        'schema': bytes.fromhex(schema_uid[2:]) if isinstance(schema_uid, str) else schema_uid,
        'recipient': recipient,
        'expirationTime': NO_EXPIRATION,  # No expiration for attestation
        'revocable': True,
        'refUID': bytes(32),  # 32 zero bytes (no reference)
        'data': encoded_data,
        'value': 0,
        'nonce': nonce,
        'deadline': deadline,  # When the signature expires
    }
    
    # Create EIP-712 encoded data
    typed_data = {
        'domain': domain,
        'primaryType': 'Attest', 
        'types': types,
        'message': message,
    }
    
    print(f"\n   EIP-712 Domain:")
    print(f"     - name: {domain['name']}")
    print(f"     - version: {domain['version']}")
    print(f"     - chainId: {domain['chainId']}")
    print(f"     - verifyingContract: {domain['verifyingContract']}")
    
    print(f"\n   Message being signed:")
    print(f"     - schema: 0x{message['schema'].hex()}")
    print(f"     - recipient: {message['recipient']}")
    print(f"     - expirationTime: {message['expirationTime']}")
    print(f"     - revocable: {message['revocable']}")
    print(f"     - refUID: 0x{message['refUID'].hex()}")
    print(f"     - data length: {len(message['data'])} bytes")
    print(f"     - value: {message['value']}")
    print(f"     - nonce: {message['nonce']}")
    print(f"     - deadline: {message['deadline']}")
    
    # Use eth_account's proper EIP-712 encoding
    encoded = encode_typed_data(full_message=typed_data)
    
    # Sign with the account's private key
    signature = account.sign_message(encoded)
    
    print(f"\n   Signature created successfully")
    print(f"   Signature length: {len(signature.signature)} bytes")
    
    return signature.signature

def main():
    # Get environment variables
    rpc_url = os.getenv("RPC_URL", "https://methodical-aged-haze.base-mainnet.quiknode.pro/be2a6f7bf2b041c1bcc41cf4a2880b239afcdeb7/")
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
    
    # Get the AttestationTracker contract
    tracker_contract = w3.eth.contract(
        address=Web3.to_checksum_address(ATTESTATION_TRACKER_ADDRESS),
        abi=ATTESTATION_TRACKER_ABI
    )
    
    # Check if contract exists and get bytecode size
    print(f"\n🔍 Verifying contract at {ATTESTATION_TRACKER_ADDRESS}:")
    bytecode = w3.eth.get_code(ATTESTATION_TRACKER_ADDRESS)
    print(f"   Contract bytecode size: {len(bytecode)} bytes")
    if len(bytecode) == 0:
        print(f"   ⚠️  WARNING: No contract found at this address!")
    else:
        print(f"   ✅ Contract exists")
    
    # Check current attestation count
    try:
        current_count = tracker_contract.functions.getNumAttestations(account.address).call()
        print(f"📊 Current attestation count for your address: {current_count}")
    except Exception as e:
        print(f"⚠️  Could not get attestation count: {e}")
        print(f"   This might indicate the contract doesn't have getNumAttestations function")
    
    print(f"\n📋 Creating delegated attestation:")
    print(f"   Schema UID: {schema_uid}")
    print(f"   AttestationTracker: {ATTESTATION_TRACKER_ADDRESS}")
    print(f"   EAS Contract: {EAS_CONTRACT_ADDRESS}")
    
    try:
        # Encode attestation data
        encoded_data = encode_attestation_data(
            agent_address=account.address,
            space_id="quorum-ai-test",
            proposal_id=f"proposal-{int(time.time())}",
            vote_choice=1,
            snapshot_sig="test-signature",
            run_id=f"run-{int(time.time())}",
            confidence=95
        )
        print(f"   Encoded data length: {len(encoded_data)} bytes")
        print(f"   Encoded data hex: 0x{encoded_data.hex()[:100]}...")
        
        # Set recipient (zero address for public attestations)
        recipient = "0x0000000000000000000000000000000000000000"
        print(f"   Recipient: {recipient}")
        
        # Get nonce for EAS delegated attestation
        # For EAS, we need to use the account's nonce from EAS contract
        nonce = w3.eth.get_transaction_count(account.address)
        
        # Set deadline (1 hour from now)
        deadline = int(time.time()) + 3600
        
        print(f"   Transaction nonce: {nonce}")
        print(f"   Deadline: {deadline} (timestamp: {deadline}, expires in 1 hour)")
        print(f"   Current time: {int(time.time())}")
        
        # Create EIP-712 signature
        print("\n🖊️  Creating EIP-712 delegated signature...")
        signature = create_delegated_attestation_signature(
            w3=w3,
            account=account,
            schema_uid=schema_uid,
            recipient=recipient,
            encoded_data=encoded_data,
            nonce=nonce,
            deadline=deadline
        )
        print(f"   Signature length: {len(signature)} bytes")
        print(f"   Signature: 0x{signature.hex()}")
        
        # Extract v, r, s from the signature
        # The signature is 65 bytes: r (32) + s (32) + v (1)
        r = signature[:32]
        s = signature[32:64]
        v = signature[64]
        
        print(f"\n📝 Signature components:")
        print(f"   r: 0x{r.hex()}")
        print(f"   s: 0x{s.hex()}")
        print(f"   v: {v}")
        
        print(f"\n📦 Building delegated attestation request:")
        print(f"   Schema UID: {schema_uid}")
        print(f"   Schema bytes: 0x{bytes.fromhex(schema_uid[2:]).hex()}")
        print(f"   Attester address: {account.address}")
        print(f"   RefUID: 0x{'0' * 64} (zero bytes)")
        print(f"   Revocable: True")
        print(f"   Value: 0 ETH")
        
        # Build delegated attestation request with nested structure matching EAS SDK
        delegated_request = (
            bytes.fromhex(schema_uid[2:]),  # schema
            (                                # data tuple (AttestationRequestData)
                recipient,                   # recipient
                NO_EXPIRATION,               # expirationTime (uint64) - 0 for no expiration
                True,                        # revocable
                bytes(32),                   # refUID (32 zero bytes for no reference)
                encoded_data,                # data (encoded attestation data)
                0                            # value (uint256) - no ETH sent
            ),
            (                                # signature tuple (v, r, s)
                v,                           # v (uint8)
                r,                           # r (bytes32)
                s                            # s (bytes32)
            ),
            account.address,                 # attester (signer's address)
            deadline                         # deadline (uint64) - signature expiration
        )
        
        print(f"\n🔍 Request structure validation:")
        print(f"   Schema: {type(delegated_request[0])} - {len(delegated_request[0])} bytes")
        print(f"   Data tuple length: {len(delegated_request[1])} items")
        print(f"   Signature tuple length: {len(delegated_request[2])} items")
        print(f"   Attester type: {type(delegated_request[3])}")
        print(f"   Deadline type: {type(delegated_request[4])}")
        
        # First try to call the function to see if it would revert
        print("\n🧪 Testing function call first...")
        try:
            # This will revert if there's an issue with the parameters
            result = tracker_contract.functions.attestByDelegation(delegated_request).call({
                'from': account.address,
                'value': 0
            })
            print(f"   ✅ Function call successful, would return: {result.hex()}")
        except Exception as e:
            print(f"   ❌ Function call failed: {e}")
            print(f"   This means the transaction would revert!")
            
            # Let's debug the signature and parameters in detail
            print(f"\n🔍 Detailed debug info:")
            print(f"   Schema: {delegated_request[0].hex()}")
            print(f"\n   Data tuple breakdown:")
            print(f"     - recipient: {delegated_request[1][0]}")
            print(f"     - expirationTime: {delegated_request[1][1]}")
            print(f"     - revocable: {delegated_request[1][2]}")
            print(f"     - refUID: 0x{delegated_request[1][3].hex()}")
            print(f"     - data length: {len(delegated_request[1][4])} bytes")
            print(f"     - data (first 50 bytes): 0x{delegated_request[1][4].hex()[:100]}...")
            print(f"     - value: {delegated_request[1][5]}")
            print(f"\n   Signature breakdown:")
            print(f"     - v: {delegated_request[2][0]} (type: {type(delegated_request[2][0])})")
            print(f"     - r: 0x{delegated_request[2][1].hex()}")
            print(f"     - s: 0x{delegated_request[2][2].hex()}")
            print(f"\n   Attester: {delegated_request[3]}")
            print(f"   Deadline: {delegated_request[4]} (type: {type(delegated_request[4])})")
            
            # Check if we're calling the right contract
            print(f"\n   Contract being called: {ATTESTATION_TRACKER_ADDRESS}")
            print(f"   Is this an EAS contract or AttestationTracker?")
            
            # Try to continue anyway to see what happens
            print(f"   Continuing with transaction anyway...")

        # Estimate gas
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
        
        # Get proper transaction nonce for the Ethereum transaction
        tx_nonce = w3.eth.get_transaction_count(account.address)
        
        # Build transaction
        tx = tracker_contract.functions.attestByDelegation(delegated_request).build_transaction({
            'from': account.address,
            'gas': gas_estimate,
            'gasPrice': int(gas_price * 1.1),  # Add 10% to gas price
            'nonce': tx_nonce,
            'chainId': 8453,  # Base mainnet
            'value': 0
        })
        
        # Sign and send transaction
        print("\n📤 Signing and sending transaction...")
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"📝 Transaction hash: {tx_hash.hex()}")
        
        # Wait for confirmation
        print("⏳ Waiting for confirmation...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt["status"] == 1:
            print("✅ Delegated attestation successful!")
            
            # Check new attestation count
            new_count = tracker_contract.functions.getNumAttestations(account.address).call()
            print(f"\n📊 New attestation count: {new_count} (was {current_count})")
            
            # Parse logs for attestation UID
            if receipt["logs"]:
                for log in receipt["logs"]:
                    if len(log['topics']) > 1:
                        print(f"📍 Event topic: {log['topics'][0].hex()}")
                        print(f"📍 Attestation UID: {log['topics'][1].hex()}")
            
            # Save details
            with open("delegated_attestation.txt", "w") as f:
                f.write(f"TRANSACTION_HASH={tx_hash.hex()}\n")
                f.write(f"BLOCK_NUMBER={receipt['blockNumber']}\n")
                f.write(f"SCHEMA_UID={schema_uid}\n")
                f.write(f"NONCE={tx_nonce}\n")
                f.write(f"DEADLINE={deadline}\n")
                f.write(f"SIGNATURE=0x{signature.hex()}\n")
            print(f"\n💾 Details saved to delegated_attestation.txt")
            
            print(f"\n🔗 View on BaseScan: https://basescan.org/tx/{tx_hash.hex()}")
            print(f"🔗 Contract: https://basescan.org/address/{ATTESTATION_TRACKER_ADDRESS}")
            
        else:
            print("❌ Transaction failed!")
            print(f"Receipt: {receipt}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()