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
GNOSIS_PRIVATE_KEY = os.getenv("EOA_PRIVATE_KEY")
GNOSIS_SAFE_ADDRESS = os.getenv("GNOSIS_SAFE_ADDRESS")
ETHEREUM_RPC_URL=f"https://base-mainnet.infura.io/v3/{os.getenv('INFURA_API_KEY')}"

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
    
    # Use checksummed address and ensure proper formatting
    from_address = Web3.to_checksum_address(account.address)
    
    # Check if proposal is a bytes32 hash (starts with 0x and is 66 chars)
    proposal_is_bytes32 = proposal.startswith("0x") and len(proposal) == 66
    
    snapshot_message = {
        "domain": {
            "name": "snapshot",
            "version": "0.1.4"
        },
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"}
            ],
            "Vote": [
                {"name": "from", "type": "string"},
                {"name": "space", "type": "string"},
                {"name": "timestamp", "type": "uint64"},
                {"name": "proposal", "type": "bytes32" if proposal_is_bytes32 else "string"},
                {"name": "choice", "type": "uint32"},
                {"name": "reason", "type": "string"},
                {"name": "app", "type": "string"},
                {"name": "metadata", "type": "string"}
            ]
        },
        "primaryType": "Vote",
        "message": {
            "from": from_address,
            "space": space,
            "timestamp": timestamp,
            "proposal": proposal,
            "choice": choice,
            "reason": "",
            "app": "",
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
    url = "https://seq.snapshot.org/"
    
    # Ensure checksummed address and properly formatted signature
    from_address = Web3.to_checksum_address(account.address)
    # Try with 0x prefix
    clean_signature = signature if signature.startswith("0x") else f"0x{signature}"
    
    # Prepare request body with correct envelope format
    request_body = {
        "address": from_address,  # This must be the EOA address that signed the message
        "sig": clean_signature,   # Remove 0x prefix if present
        "data": {
            "domain": snapshot_message["domain"],
            "types": snapshot_message["types"],
            "message": snapshot_message["message"]
        }
    }
    
    # Send POST request
    headers = {"Content-Type": "application/json"}
    
    response = None
    try:
        response = requests.post(url, json=request_body, headers=headers)
        response.raise_for_status()
        return {"success": True, "response": response.json()}
    except requests.exceptions.RequestException as e:
        response_text = None
        if response is not None:
            response_text = response.text
        return {"success": False, "error": str(e), "response_text": response_text}



def test_snapshot_voting():
    """Test function for Snapshot voting functionality."""
    print("=== Testing Snapshot Voting ===\n")
    
    # Test parameters
    space = "spectradao.eth"
    proposal = "0xfbfc4f16d1f44d4298f4a7c958e3ad158ec0c8fc582d1151f766c26dbe50b237"
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
    print("Signing message with EOA...")
    signature = sign_snapshot_message(vote_message)
    print(f"  Signature: {signature[:20]}...{signature[-20:]}")
    
    # Send vote to Snapshot
    print("Sending vote to Snapshot Hub...")
    result = send_vote_to_snapshot(vote_message, signature)
    
    if result["success"]:
        print("✅ Vote submitted successfully!")
        print(f"  Response: {result['response']}")
    else:
        print("❌ Vote submission failed!")
        print(f"  Error: {result['error']}")
        if result.get("response_text"):
            print(f"  Response text: {result['response_text']}")
    
    return vote_message


if __name__ == "__main__":
    test_snapshot_voting()
