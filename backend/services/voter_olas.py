"""OLAS-native voting script assuming all OLAS integration points are provided."""

import json
import os
import time
from datetime import date

import requests
from eth_account.messages import encode_typed_data
from safe_eth.eth import EthereumClient
from safe_eth.safe import Safe
from safe_eth.safe.api import TransactionServiceApi
from web3 import Web3

from utils.env_helper import get_env_with_prefix

# --- OLAS INTEGRATION: Read from OLAS-provided sources ---
# OLAS provides private key in file
with open("ethereum_private_key.txt") as f:
    EOA_PRIVATE_KEY = f.read().strip()

# OLAS provides Safe addresses as JSON environment variable
SAFE_ADDRESSES = json.loads(get_env_with_prefix("SAFE_CONTRACT_ADDRESSES", "{}"))

# OLAS provides RPC endpoints for all supported chains
RPC_ENDPOINTS = {
    "ethereum": get_env_with_prefix("ETHEREUM_LEDGER_RPC"),
    "gnosis": get_env_with_prefix("GNOSIS_LEDGER_RPC"),
    "base": get_env_with_prefix("BASE_LEDGER_RPC"),
    "celo": get_env_with_prefix("CELO_LEDGER_RPC"),
    "mode": get_env_with_prefix("MODE_LEDGER_RPC"),
}

# OLAS provides staking and activity tracking configuration
STAKING_TOKEN_CONTRACT = get_env_with_prefix("STAKING_TOKEN_CONTRACT_ADDRESS")
ACTIVITY_CHECKER_CONTRACT = get_env_with_prefix("ACTIVITY_CHECKER_CONTRACT_ADDRESS")
STORE_PATH = get_env_with_prefix("STORE_PATH")  # For persistent data storage

# Safe transaction service URLs for supported chains
SAFE_SERVICE_URLS = {
    "ethereum": "https://safe-transaction-mainnet.safe.global/",
    "gnosis": "https://safe-transaction-gnosis-chain.safe.global/",
    "base": "https://safe-transaction-base.safe.global/",
    "celo": "https://safe-transaction-celo.safe.global/",
    "mode": "https://safe-transaction-mode.safe.global/",
}


# --- ACTIVITY TRACKING FOR OLAS ---
class OLASActivityTracker:
    def __init__(self):
        self.last_activity_date = None
        self.last_tx_hash = None
        self.persistent_file = (
            os.path.join(STORE_PATH, "activity_tracker.json")
            if STORE_PATH
            else "activity_tracker.json"
        )
        self.load_state()

    def load_state(self):
        """Load activity state from persistent storage."""
        try:
            if os.path.exists(self.persistent_file):
                with open(self.persistent_file) as f:
                    data = json.load(f)
                    self.last_activity_date = (
                        date.fromisoformat(data["last_activity_date"])
                        if data.get("last_activity_date")
                        else None
                    )
                    self.last_tx_hash = data.get("last_tx_hash")
        except Exception:
            pass

    def save_state(self):
        """Save activity state to persistent storage."""
        try:
            os.makedirs(os.path.dirname(self.persistent_file), exist_ok=True)
            with open(self.persistent_file, "w") as f:
                json.dump(
                    {
                        "last_activity_date": self.last_activity_date.isoformat()
                        if self.last_activity_date
                        else None,
                        "last_tx_hash": self.last_tx_hash,
                    },
                    f,
                )
        except Exception:
            pass

    def is_daily_activity_needed(self) -> bool:
        """Check if we need to create activity for today for OLAS staking."""
        return self.last_activity_date != date.today()

    def mark_activity_completed(self, tx_hash: str):
        """Mark daily activity as completed for OLAS tracking."""
        self.last_activity_date = date.today()
        self.last_tx_hash = tx_hash
        self.save_state()


# Global OLAS activity tracker
activity_tracker = OLASActivityTracker()


# --- WEB3 CONNECTIONS ---
def get_web3_connection(chain: str) -> Web3:
    """Get Web3 connection for specified chain using OLAS-provided RPC."""
    rpc_url = RPC_ENDPOINTS.get(chain)
    if not rpc_url:
        msg = f"No OLAS RPC endpoint configured for chain: {chain}"
        raise ValueError(msg)

    w3 = Web3(Web3.HTTPProvider(rpc_url))
    if not w3.is_connected():
        msg = f"Failed to connect to {chain} network via OLAS RPC"
        raise ConnectionError(msg)

    return w3


# Create account from OLAS-provided private key
w3 = get_web3_connection("gnosis")  # Use Gnosis as default for account creation
account = w3.eth.account.from_key(EOA_PRIVATE_KEY)


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

    from_address = Web3.to_checksum_address(account.address)
    proposal_is_bytes32 = proposal.startswith("0x") and len(proposal) == 66

    return {
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


def sign_snapshot_message(snapshot_message: dict) -> str:
    """Sign a Snapshot vote message with the OLAS-provided EOA private key.

    Args:
        snapshot_message: The vote message dictionary from create_snapshot_vote_message

    Returns:
        Hex string of the signature
    """
    signable_message = encode_typed_data(full_message=snapshot_message)
    signed = account.sign_message(signable_message)
    return signed.signature.hex()


def select_optimal_chain_for_activity() -> str:
    """Select the cheapest chain for OLAS activity transactions."""
    # Priority order: cheapest to most expensive gas fees
    chain_priority = ["gnosis", "celo", "mode", "base", "ethereum"]

    for chain in chain_priority:
        if chain in SAFE_ADDRESSES and chain in RPC_ENDPOINTS and RPC_ENDPOINTS[chain]:
            return chain

    # Fallback to first available
    available_chains = [chain for chain in SAFE_ADDRESSES if RPC_ENDPOINTS.get(chain)]

    if available_chains:
        return available_chains[0]

    msg = "No valid chain configuration found in OLAS setup"
    raise ValueError(msg)


def perform_olas_safe_activity_transaction(chain: str | None = None) -> dict:
    """Perform Safe transaction for OLAS daily activity requirement.

    Creates a 0-ETH transaction from the Safe to itself to satisfy OLAS activity tracking.
    As per Julinda: "one multi-sig goes through that agent's safe"
    """

    if not chain:
        chain = select_optimal_chain_for_activity()

    try:
        safe_address = SAFE_ADDRESSES.get(chain)
        if not safe_address:
            msg = f"No Safe address configured for chain: {chain}"
            raise ValueError(msg)

        safe_address = Web3.to_checksum_address(safe_address)

        # Get Web3 and Ethereum client using OLAS-provided RPC
        w3 = get_web3_connection(chain)
        eth_client = EthereumClient(RPC_ENDPOINTS[chain])

        # Initialize Safe instance
        safe_instance = Safe(safe_address, eth_client)

        # Get Safe service for this chain
        safe_service_url = SAFE_SERVICE_URLS.get(chain)
        if not safe_service_url:
            msg = f"No Safe service URL configured for chain: {chain}"
            raise ValueError(msg)

        safe_service = TransactionServiceApi(network=chain, base_url=safe_service_url)

        # Build dummy transaction: 0 ETH to self (minimal cost for OLAS activity)
        safe_tx = safe_instance.build_multisig_tx(
            to=safe_address,  # Send to itself
            value=0,  # 0 ETH value
            data=b"",  # Empty data
            operation=0,  # CALL operation
        )

        # Sign Safe transaction hash with OLAS-provided EOA private key
        signed_safe_tx_hash = account.unsafe_sign_hash(safe_tx.safe_tx_hash)
        safe_tx.signatures = signed_safe_tx_hash.signature

        # Propose transaction to Safe Transaction Service
        safe_service.post_transaction(safe_tx)

        # Execute Safe transaction on-chain
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
            tx_sender_private_key=EOA_PRIVATE_KEY,
        )

        tx_hash = ethereum_tx_sent.tx_hash

        # Wait for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt["status"] == 1:
            # Mark OLAS activity as completed
            activity_tracker.mark_activity_completed(tx_hash.hex())

            return {
                "success": True,
                "tx_hash": tx_hash.hex(),
                "chain": chain,
                "safe_address": safe_address,
                "block_number": receipt["blockNumber"],
                "gas_used": receipt["gasUsed"],
            }
        return {
            "success": False,
            "error": "Transaction reverted",
            "tx_hash": tx_hash.hex(),
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def send_vote_to_snapshot(snapshot_message: dict, signature: str) -> dict:
    """Send a signed vote to Snapshot Hub API and ensure OLAS activity.

    Args:
        snapshot_message: The vote message dictionary
        signature: The hex signature string

    Returns:
        API response dictionary with OLAS activity status
    """

    # Snapshot Hub API endpoint
    url = "https://seq.snapshot.org/"

    # Prepare Snapshot vote request
    from_address = Web3.to_checksum_address(account.address)
    clean_signature = signature if signature.startswith("0x") else f"0x{signature}"

    request_body = {
        "address": from_address,
        "sig": clean_signature,
        "data": {
            "domain": snapshot_message["domain"],
            "types": snapshot_message["types"],
            "message": snapshot_message["message"],
        },
    }

    # Submit Snapshot vote
    response = None
    snapshot_result = {"success": False, "error": "Unknown error"}

    try:
        response = requests.post(
            url, json=request_body, headers={"Content-Type": "application/json"}
        )
        snapshot_result = {"success": True, "response": response.json()}
    except requests.exceptions.RequestException as e:
        response_text = response.text if response else None
        snapshot_result = {
            "success": False,
            "error": str(e),
            "response_text": response_text,
        }

    # OLAS Activity Requirement: Ensure daily Safe transaction
    if activity_tracker.is_daily_activity_needed():
        olas_activity_result = perform_olas_safe_activity_transaction()
        snapshot_result["olas_activity"] = olas_activity_result
    else:
        snapshot_result["olas_activity"] = {
            "success": True,
            "message": "Daily activity already completed",
            "last_tx_hash": activity_tracker.last_tx_hash,
            "last_activity_date": activity_tracker.last_activity_date.isoformat(),
        }

    return snapshot_result


def test_snapshot_voting():
    """Test function for Snapshot voting with OLAS integration."""

    # Test parameters
    space = "spectradao.eth"
    proposal = "0xfbfc4f16d1f44d4298f4a7c958e3ad158ec0c8fc582d1151f766c26dbe50b237"
    choice = 1  # 1 = For

    # Create vote message
    vote_message = create_snapshot_vote_message(space, proposal, choice)

    # Sign message with OLAS-provided EOA
    signature = sign_snapshot_message(vote_message)

    # Send vote to Snapshot with OLAS activity handling
    result = send_vote_to_snapshot(vote_message, signature)

    # Display results
    if result["success"] or result.get("response_text"):
        pass

    # Display OLAS activity status
    if "olas_activity" in result:
        if result["olas_activity"]["success"]:
            if (
                "tx_hash" in result["olas_activity"]
                or "last_tx_hash" in result["olas_activity"]
            ):
                pass
        else:
            pass

    return vote_message


if __name__ == "__main__":
    test_snapshot_voting()
