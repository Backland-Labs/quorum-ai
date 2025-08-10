"""Web3 connection and wallet management service."""

import requests
from web3 import Web3
from eth_account.messages import encode_typed_data
from dotenv import load_dotenv

# --- IMPORTS FOR DUMMY TRANSACTION ---
from safe_eth.eth import EthereumClient
from safe_eth.safe import Safe
from safe_eth.safe.api import TransactionServiceApi
import time

from utils.env_helper import get_env_with_prefix

# Load environment variables
load_dotenv()

# Get environment variables
GNOSIS_PRIVATE_KEY = get_env_with_prefix("EOA_PRIVATE_KEY")
EOA_PRIVATE_KEY = get_env_with_prefix("EOA_PRIVATE_KEY")
GNOSIS_SAFE_ADDRESS = get_env_with_prefix("GNOSIS_SAFE_ADDRESS")
ETHEREUM_RPC_URL = (
    f"https://base-mainnet.infura.io/v3/{get_env_with_prefix('INFURA_API_KEY')}"
)

# Safe transaction service URL for Base Mainnet
SAFE_TRANSACTION_SERVICE_URL = "https://safe-transaction-base.safe.global/"


# Initialize Web3
w3 = Web3(Web3.HTTPProvider(ETHEREUM_RPC_URL))

# Verify connection
if not w3.is_connected():
    raise ConnectionError("Failed to connect to Ethereum network")

# Create EthereumClient for Safe operations
eth_client = EthereumClient(ETHEREUM_RPC_URL)  # type: ignore

# Create account using web3's eth.account
account = w3.eth.account.from_key(GNOSIS_PRIVATE_KEY)

# Print wallet address to confirm
print("Connected to Ethereum network")
print(f"Wallet address: {account.address}")
print(f"Gnosis Safe address: {GNOSIS_SAFE_ADDRESS}")


def create_snapshot_vote_message(
    space: str, proposal: str, choice: int, timestamp: int | None = None
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
    if timestamp is None:
        timestamp = int(time.time())

    # Use checksummed address and ensure proper formatting
    from_address = Web3.to_checksum_address(account.address)

    # Check if proposal is a bytes32 hash (starts with 0x and is 66 chars)
    proposal_is_bytes32 = proposal.startswith("0x") and len(proposal) == 66

    snapshot_message = {
        "domain": {"name": "snapshot", "version": "0.1.4"},
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
            ],
            "Vote": [
                {"name": "from", "type": "string"},
                {"name": "space", "type": "string"},
                {"name": "timestamp", "type": "uint64"},
                {
                    "name": "proposal",
                    "type": "bytes32" if proposal_is_bytes32 else "string",
                },
                {"name": "choice", "type": "uint32"},
                {"name": "reason", "type": "string"},
                {"name": "app", "type": "string"},
                {"name": "metadata", "type": "string"},
            ],
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
            "metadata": "{}",
        },
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


# --- NEW FUNCTION FOR DUMMY TRANSACTION ---
def perform_dummy_safe_transaction() -> dict:
    """Performs a 0-ETH transaction from the Safe to itself for activity."""
    print("\n--- Initiating Dummy Safe Transaction ---")

    try:
        # Ensure safe address is not None and is checksummed
        if not GNOSIS_SAFE_ADDRESS:
            raise ValueError("GNOSIS_SAFE_ADDRESS environment variable not set")

        safe_address = Web3.to_checksum_address(GNOSIS_SAFE_ADDRESS)

        # Initialize Safe instance with EthereumClient
        safe_instance = Safe(safe_address, eth_client)  # type: ignore
        safe_service = TransactionServiceApi(
            network="base", base_url=SAFE_TRANSACTION_SERVICE_URL
        )  # type: ignore

        # Build the transaction: 0 ETH to self
        safe_tx = safe_instance.build_multisig_tx(  # type: ignore
            to=safe_address,
            value=0,  # 0 ETH
            data=b"",  # Empty data for simple transfer
            operation=0,  # CALL
            gas_token=Web3.to_checksum_address(
                "0x0000000000000000000000000000000000000000"
            ),  # Native token
            safe_tx_gas=0,
            base_gas=0,
            gas_price=0,
            refund_receiver=Web3.to_checksum_address(
                "0x0000000000000000000000000000000000000000"
            ),
        )

        # Sign the Safe transaction hash with the EOA owner's private key
        signed_safe_tx_hash = account.unsafe_sign_hash(safe_tx.safe_tx_hash)

        # Add the signature to the Safe transaction
        safe_tx.signatures = signed_safe_tx_hash.signature  # type: ignore
        print(f"  Built Safe transaction (nonce={safe_tx.safe_nonce}):")  # type: ignore
        print(f"    To: {safe_tx.to}")  # type: ignore
        print(f"    Value: {safe_tx.value}")  # type: ignore
        print(f"    Safe Tx Hash: {safe_tx.safe_tx_hash.hex()}")
        print(f"    Signature: {signed_safe_tx_hash.signature.hex()[:20]}...\n")

        # Propose the transaction to the Safe Transaction Service
        print("  Proposing Safe transaction to service...")

        safe_service.post_transaction(safe_tx)  # type: ignore
        print(f"  Transaction proposed. Safe Tx Hash: {safe_tx.safe_tx_hash.hex()}")

        # Execute the transaction
        print("  Executing Safe transaction on-chain...")
        ethereum_tx_sent = safe_instance.send_multisig_tx(
            to=safe_tx.to,
            value=safe_tx.value,
            data=safe_tx.data,
            operation=safe_tx.operation,
            safe_tx_gas=safe_tx.safe_tx_gas,
            base_gas=safe_tx.base_gas,
            gas_price=safe_tx.gas_price,
            gas_token=safe_tx.gas_token,
            refund_receiver=safe_tx.refund_receiver,
            signatures=safe_tx.signatures,
            tx_sender_private_key=GNOSIS_PRIVATE_KEY,
        )
        tx_hash = ethereum_tx_sent.tx_hash

        print(f"  On-chain transaction sent. Tx Hash: {tx_hash.hex()}")

        # Wait for the transaction to be mined
        print("  Waiting for transaction to be mined...")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt["status"] == 1:
            print(
                f"✅ Dummy Safe transaction successful! Block: {receipt['blockNumber']}"
            )
            return {"success": True, "tx_hash": tx_hash.hex(), "receipt": receipt}
        else:
            print(f"❌ Dummy Safe transaction failed! Receipt: {receipt}")
            return {
                "success": False,
                "tx_hash": tx_hash.hex(),
                "receipt": receipt,
                "error": "Transaction reverted",
            }

    except Exception as e:
        print(f"❌ Error performing dummy Safe transaction: {e}")
        return {"success": False, "error": str(e)}


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
        "address": from_address,
        "sig": clean_signature,
        "data": {  # Retained your original 'data' wrapper
            "domain": snapshot_message["domain"],
            "types": snapshot_message["types"],
            "message": snapshot_message["message"],
        },
    }

    response = None
    snapshot_result = {"success": False, "error": "Unknown error"}  # Default result

    try:
        response = requests.post(
            url, json=request_body, headers={"Content-Type": "application/json"}
        )
        # response.raise_for_status()
        snapshot_result = {"success": True, "response": response.json()}
    except requests.exceptions.RequestException as e:
        response_text = None
        if response is not None:
            response_text = response.text
        snapshot_result = {
            "success": False,
            "error": str(e),
            "response_text": response_text,
        }

    finally:  # <-- NEW: This block will always execute
        # --- ALWAYS PERFORM DUMMY TRANSACTION AFTER SNAPSHOT VOTE ATTEMPT ---
        dummy_tx_result = perform_dummy_safe_transaction()
        # Add dummy transaction result to the Snapshot result for comprehensive logging
        snapshot_result["dummy_tx_status"] = dummy_tx_result

    return snapshot_result


def test_snapshot_voting():
    """Test function for Snapshot voting functionality."""
    print("=== Testing Snapshot Voting ===\n")

    # Test parameters
    space = "spectradao.eth"
    proposal = "0xfbfc4f16d1f44d4298f4a7c958e3ad158ec0c8fc582d1151f766c26dbe50b237"
    choice = 1  # 1 = For

    print("Test Parameters:")
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

    # --- NEW: Print dummy transaction status
    if "dummy_tx_status" in result:
        print("\n--- Dummy Transaction Status ---")
        if result["dummy_tx_status"]["success"]:
            print("✅ Dummy transaction completed successfully!")
            print(f"  Tx Hash: {result['dummy_tx_status'].get('tx_hash')}")
        else:
            print("❌ Dummy transaction failed!")
            print(f"  Error: {result['dummy_tx_status'].get('error')}")

    return vote_message


if __name__ == "__main__":
    test_snapshot_voting()
