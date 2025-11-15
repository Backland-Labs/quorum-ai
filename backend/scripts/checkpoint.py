#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "web3>=7.12.0",
#   "eth-account>=0.13.7",
#   "pydantic>=2.10.0",
#   "pydantic-settings>=2.6.0",
#   "pydantic-ai",
#   "python-dotenv>=1.0.0",
#   "httpx>=0.28.0",
#   "safe-eth-py>=7.7.0",
#   "requests>=2.32.4",
# ]
# ///
"""Call checkpoint on staking contract every 24 hours."""

import sys
from pathlib import Path
from web3 import Web3
from eth_account import Account

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from logging_config import setup_pearl_logger
from services.key_manager import KeyManager

logger = setup_pearl_logger(__name__)

# Default staking contract address (can be overridden via env)
STAKING_CONTRACT_ADDRESS = "0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb"

# Minimal ABI for checkpoint function
STAKING_ABI = [
    {
        "inputs": [],
        "name": "checkpoint",
        "outputs": [
            {"type": "uint256[]"},
            {"type": "uint256[]"},
            {"type": "uint256[]"},
            {"type": "uint256[]"}
        ],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


def main():
    """Call checkpoint on staking contract."""
    logger.info("Starting checkpoint call")

    try:
        # Get staking contract address (can be overridden)
        contract_address = getattr(settings, 'staking_contract_address', None) or STAKING_CONTRACT_ADDRESS

        # Setup Web3
        rpc_url = settings.base_ledger_rpc
        if not rpc_url:
            logger.error("BASE_LEDGER_RPC not configured")
            print("Error: BASE_LEDGER_RPC not configured")
            sys.exit(1)

        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            logger.error(f"Cannot connect to RPC: {rpc_url}")
            print(f"Error: Cannot connect to RPC: {rpc_url}")
            sys.exit(1)

        logger.info(f"Connected to chain_id={w3.eth.chain_id}")

        # Load private key using KeyManager
        key_manager = KeyManager()
        private_key = key_manager.get_private_key()
        account = Account.from_key(private_key)

        logger.info(f"Using account: {account.address}")

        # Initialize contract
        contract = w3.eth.contract(
            address=contract_address,
            abi=STAKING_ABI
        )

        logger.info(f"Calling checkpoint on contract: {contract_address}")

        # Build transaction
        nonce = w3.eth.get_transaction_count(account.address)
        gas_price = w3.eth.gas_price

        tx = contract.functions.checkpoint().build_transaction({
            'from': account.address,
            'nonce': nonce,
            'gas': 500000,
            'gasPrice': gas_price
        })

        # Sign transaction
        signed_tx = account.sign_transaction(tx)

        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        logger.info(f"Transaction sent: {tx_hash.hex()}")
        print(f"Transaction sent: {tx_hash.hex()}")

        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] == 1:
            gas_used = receipt['gasUsed']
            block_number = receipt['blockNumber']

            logger.info(
                f"Checkpoint successful! "
                f"tx_hash={tx_hash.hex()}, "
                f"gas_used={gas_used}, "
                f"block={block_number}"
            )
            print(f"Success: {tx_hash.hex()}")
            print(f"Gas used: {gas_used}")
            print(f"Block: {block_number}")
        else:
            logger.error(f"Transaction reverted: {tx_hash.hex()}")
            print(f"Error: Transaction reverted: {tx_hash.hex()}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Checkpoint failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        print(f"Error: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
