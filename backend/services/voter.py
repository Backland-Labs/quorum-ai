"""Web3 connection and wallet management service."""

import os
import json
import requests
from web3 import Web3
from eth_account.messages import encode_typed_data
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get environment variables
GNOSIS_PRIVATE_KEY = os.getenv("GNOSIS_PRIVATE_KEY")
GNOSIS_SAFE_ADDRESS = os.getenv("GNOSIS_SAFE_ADDRESS")
ETHEREUM_RPC_URL=f"https://sepolia.infura.io/v3/{os.getenv('INFURA_API_KEY')}"

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC_URL))

# Verify connection
if not w3.is_connected():
    raise ConnectionError("Failed to connect to Ethereum network")

# Create account using web3's eth.account
account = w3.eth.account.from_key(GNOSIS_PRIVATE_KEY)

# Print wallet address to confirm
print(f"Connected to Ethereum network")
print(f"Wallet address: {account.address}")
print(f"Gnosis Safe address: {GNOSIS_SAFE_ADDRESS}")


def create_snapshot_vote_message(
    space: str,
    proposal: str,
    choice: int,
    timestamp: int | None = None
) -> dict:
    """Create a Snapshot vote message payload.
    
    Args:
        space: The Snapshot space ID (e.g., "aave.eth")
        proposal: The proposal ID (IPFS hash)
        choice: Vote choice (1 = For, 2 = Against, 3 = Abstain)
        timestamp: Unix timestamp in seconds (defaults to current time)
        
    Returns:
        Dictionary containing the vote message structure
    """
    import time
    
    if timestamp is None:
        timestamp = int(time.time())
    
    snapshot_message = {
        "domain": {
            "name": "snapshot",
            "version": "0.1.4"
        },
        "types": {
            "Vote": [
                {"name": "from", "type": "address"},
                {"name": "space", "type": "string"},
                {"name": "timestamp", "type": "uint64"},
                {"name": "proposal", "type": "string"},
                {"name": "choice", "type": "uint32"},
                {"name": "metadata", "type": "string"}
            ]
        },
        "primaryType": "Vote",
        "message": {
            "from": account.address,
            "space": space,
            "timestamp": timestamp,
            "proposal": proposal,
            "choice": choice,
            "metadata": "{}"
        }
    }
    
    return snapshot_message


def sign_snapshot_message(snapshot_message: dict) -> str:
    """Sign a Snapshot vote message with the EOA private key.
    
    This signs the message with the EOA that is an owner of the Gnosis Safe,
    allowing Snapshot to verify ownership/delegation rights.
    
    Args:
        snapshot_message: The vote message dictionary from create_snapshot_vote_message
        
    Returns:
        Hex string of the signature
    """

    # Sign the EIP-712 structured data
    # Use the full_message parameter since we have the complete structure
    signable_message = encode_typed_data(full_message=snapshot_message)
    signed = account.sign_message(signable_message)
    
    # Return the signature as hex string
    return signed.signature.hex()


def send_vote_to_snapshot(snapshot_message: dict, signature: str) -> dict:
    """Send a signed vote to Snapshot Hub API.
    
    Args:
        snapshot_message: The vote message dictionary
        signature: The hex signature string
        
    Returns:
        API response dictionary
    """
    # Snapshot Hub API endpoint
    url = "https://testnet.hub.snapshot.org/api/msg"
    
    # Prepare request body with correct envelope format
    request_body = {
        "address": GNOSIS_SAFE_ADDRESS,  # Voting address (Safe)
        "sig": signature,
        "data": {
            "domain": snapshot_message["domain"],
            "types": snapshot_message["types"],
            "message": snapshot_message["message"]
        }
    }
    
    # Send POST request
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=request_body, headers=headers)
        print(response.text)
        response.raise_for_status()
        return {"success": True, "response": response.json()}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}


def test_snapshot_voting():
    """Test function for Snapshot voting functionality."""
    print("=== Testing Snapshot Voting ===\n")
    
    # Test parameters
    space = "aave.eth"
    proposal = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
    choice = 1  # 1 = For
    
    print(f"Test Parameters:")
    print(f"  Space: {space}")
    print(f"  Proposal: {proposal}")
    print(f"  Choice: {choice} (For)")
    print(f"  EOA Address: {account.address}")
    print(f"  Gnosis Safe: {GNOSIS_SAFE_ADDRESS}\n")
    
    # Create vote message
    print("Creating vote message...")
    vote_message = create_snapshot_vote_message(space, proposal, choice)
    print(f"  Timestamp: {vote_message['message']['timestamp']}")
    
    # Sign message
    print("\nSigning message with EOA...")
    signature = sign_snapshot_message(vote_message)
    print(f"  Signature: {signature[:20]}...{signature[-20:]}")
    
    # Prepare complete payload
    vote_payload = {
        "address": GNOSIS_SAFE_ADDRESS,
        "sig": signature,
        "data": {
            "domain": vote_message["domain"],
            "types": vote_message["types"],
            "message": vote_message["message"]
        }
    }
    
    print("\n✅ Vote payload ready for Snapshot API")
    print(f"  Voting address (Safe): {vote_payload['address']}")
    print(f"  Signer (EOA): {account.address}")
    
    # Send vote to Snapshot
    print("\nSending vote to Snapshot Hub...")
    result = send_vote_to_snapshot(vote_message, signature)
    print(result)
    
    if result["success"]:
        print("✅ Vote submitted successfully!")
        print(f"  Response: {result['response']}")
    else:
        print("❌ Vote submission failed!")
        print(f"  Error: {result['error']}")
    
    return vote_payload


if __name__ == "__main__":
    test_snapshot_voting()
