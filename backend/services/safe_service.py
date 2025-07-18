"""Safe transaction service for handling multi-signature wallet operations."""

import json
from typing import Dict, Optional, Any
from web3 import Web3
from eth_account import Account
from safe_eth.eth import EthereumClient
from safe_eth.safe import Safe
from safe_eth.safe.api import TransactionServiceApi

from config import settings
from utils.vote_encoder import encode_cast_vote, Support
from services.governor_registry import get_governor, GovernorRegistryError
from logging_config import setup_pearl_logger, log_span


# Constants for Safe service URLs
SAFE_SERVICE_URLS = {
    "ethereum": "https://safe-transaction-mainnet.safe.global/",
    "gnosis": "https://safe-transaction-gnosis-chain.safe.global/",
    "base": "https://safe-transaction-base.safe.global/",
    "mode": "https://safe-transaction-mode.safe.global/",
}

# Chain ID mapping for governor vote support
CHAIN_ID_TO_NAME = {
    1: "ethereum",
    11155111: "ethereum",  # Sepolia testnet maps to ethereum
    100: "gnosis",
    8453: "base",
    34443: "mode",
}

# Safe operation types
SAFE_OPERATION_CALL = 0
SAFE_OPERATION_DELEGATECALL = 1


class SafeService:
    """Service for handling Safe multi-signature wallet transactions."""

    def __init__(self):
        """Initialize Safe service with configuration."""
        self.logger = setup_pearl_logger(__name__)
        self.safe_addresses = json.loads(settings.safe_contract_addresses)
        self.rpc_endpoints = {
            "ethereum": settings.ethereum_ledger_rpc,
            "gnosis": settings.gnosis_ledger_rpc,
            "base": settings.base_ledger_rpc,
            "mode": settings.mode_ledger_rpc,
        }

        # Initialize account from private key
        with open("ethereum_private_key.txt", "r") as f:
            private_key = f.read().strip()

        self.account = Account.from_key(private_key)
        self._web3_connections = {}

        # Log initialization details
        eoa_address = self.account.address
        configured_safes = list(self.safe_addresses.keys())
        available_chains = list(self.rpc_endpoints.keys())
        
        self.logger.info(
            f"SafeService initialized (eoa_address={eoa_address}, "
            f"safe_addresses={configured_safes}, "
            f"available_chains={available_chains})"
        )

    def get_web3_connection(self, chain: str) -> Web3:
        """Get Web3 connection for specified chain.

        Args:
            chain: Blockchain network name

        Returns:
            Web3 instance connected to the chain

        Raises:
            ValueError: If no RPC endpoint configured for chain
            ConnectionError: If connection to network fails
        """
        if chain in self._web3_connections:
            return self._web3_connections[chain]

        rpc_url = self.rpc_endpoints.get(chain)
        if not rpc_url:
            raise ValueError(f"No RPC endpoint configured for chain: {chain}")

        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if not w3.is_connected():
            raise ConnectionError(f"Failed to connect to {chain} network")

        self._web3_connections[chain] = w3
        return w3

    def select_optimal_chain(self) -> str:
        """Select the cheapest chain for Safe transactions.

        Returns:
            Chain name with lowest expected gas costs

        Raises:
            ValueError: If no valid chain configuration found
        """
        # Priority order: cheapest to most expensive gas fees
        chain_priority = ["gnosis", "celo", "mode", "base", "ethereum"]

        for chain in chain_priority:
            if (
                chain in self.safe_addresses
                and chain in self.rpc_endpoints
                and self.rpc_endpoints[chain]
            ):
                return chain

        # Fallback to first available
        available_chains = [
            chain
            for chain in self.safe_addresses.keys()
            if chain in self.rpc_endpoints and self.rpc_endpoints[chain]
        ]

        if available_chains:
            return available_chains[0]

        raise ValueError("No valid chain configuration found")

    async def _submit_safe_transaction(
        self,
        *,
        chain: str,
        to: str,
        value: int,
        data: bytes,
        operation: int = SAFE_OPERATION_CALL
    ) -> Dict[str, Any]:
        """Submit a Safe transaction with the given parameters.
        
        Args:
            chain: Blockchain network name
            to: Transaction recipient address
            value: ETH value to send (in wei)
            data: Transaction data
            operation: Safe operation type (0=CALL, 1=DELEGATECALL)
            
        Returns:
            Dict with transaction details and success status
        """
        # Runtime assertions for critical inputs
        assert isinstance(chain, str) and chain, "Chain must be a non-empty string"
        assert isinstance(to, str) and to, "To address must be a non-empty string"
        assert isinstance(value, int) and value >= 0, "Value must be a non-negative integer"
        assert isinstance(data, bytes), "Data must be bytes"
        
        with log_span(self.logger, "safe_service._submit_safe_transaction", chain=chain, to=to):
            self.logger.info(f"Creating Safe transaction on {chain} to {to}")

            try:
                safe_address = self.safe_addresses.get(chain)
                if not safe_address:
                    raise ValueError(f"No Safe address configured for chain: {chain}")

                safe_address = Web3.to_checksum_address(safe_address)

                # Get Web3 and Ethereum client
                w3 = self.get_web3_connection(chain)
                eth_client = EthereumClient(self.rpc_endpoints[chain])  # type: ignore

                # Initialize Safe instance
                safe_instance = Safe(safe_address, eth_client)  # type: ignore

                # Get Safe service for this chain
                safe_service_url = SAFE_SERVICE_URLS.get(chain)
                if not safe_service_url:
                    raise ValueError(
                        f"No Safe service URL configured for chain: {chain}"
                    )

                safe_service = TransactionServiceApi(
                    network=chain,  # type: ignore
                    base_url=safe_service_url,
                )

                # Build Safe transaction
                safe_tx = safe_instance.build_multisig_tx(
                    to=to,
                    value=value,
                    data=data,
                    operation=operation,
                )

                # Sign Safe transaction hash
                signed_safe_tx_hash = self.account.unsafe_sign_hash(
                    safe_tx.safe_tx_hash
                )
                safe_tx.signatures = signed_safe_tx_hash.signature

                # Extract transaction details for cleaner logging
                data_length = len(data)
                nonce = safe_tx.safe_nonce
                tx_hash = safe_tx.safe_tx_hash.hex()
                
                self.logger.info(
                    f"Built Safe transaction (chain={chain}, safe_address={safe_address}, "
                    f"to={to}, value={value}, data_length={data_length}, "
                    f"nonce={nonce}, safe_tx_hash={tx_hash})"
                )

                # Propose transaction to Safe Transaction Service
                safe_service.post_transaction(safe_tx)
                self.logger.info("Proposed transaction to Safe service")

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
                    tx_sender_private_key=self.account.address,
                )

                tx_hash = ethereum_tx_sent.tx_hash
                self.logger.info(f"Executed Safe transaction on-chain (tx_hash={tx_hash.hex()})")

                # Wait for confirmation
                receipt = w3.eth.wait_for_transaction_receipt(tx_hash)  # type: ignore

                # Extract receipt details for cleaner code
                tx_hash_hex = tx_hash.hex()
                block_number = receipt["blockNumber"]
                gas_used = receipt["gasUsed"]
                tx_successful = receipt["status"] == 1
                
                if tx_successful:
                    self.logger.info(
                        f"Transaction successful (tx_hash={tx_hash_hex}, "
                        f"block_number={block_number}, gas_used={gas_used})"
                    )

                    return {
                        "success": True,
                        "tx_hash": tx_hash_hex,
                        "chain": chain,
                        "safe_address": safe_address,
                        "block_number": block_number,
                        "gas_used": gas_used,
                    }
                else:
                    self.logger.error(f"Transaction reverted (tx_hash={tx_hash_hex})")
                    return {
                        "success": False,
                        "error": "Transaction reverted",
                        "tx_hash": tx_hash_hex,
                    }

            except Exception as e:
                self.logger.error(f"Error creating Safe transaction: {str(e)}")
                return {"success": False, "error": str(e)}

    async def perform_activity_transaction(
        self, chain: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform Safe transaction for daily activity requirement.

        Creates a 0-ETH transaction from the Safe to itself to satisfy activity tracking.

        Args:
            chain: Specific chain to use, or None to select optimal

        Returns:
            Dict with transaction details and success status
        """
        if not chain:
            chain = self.select_optimal_chain()

        safe_address = self.safe_addresses.get(chain)
        if not safe_address:
            return {"success": False, "error": f"No Safe address configured for chain: {chain}"}

        # Use helper method to submit dummy transaction
        return await self._submit_safe_transaction(
            chain=chain,
            to=safe_address,  # Send to itself
            value=0,  # 0 ETH value
            data=b"",  # Empty data
            operation=SAFE_OPERATION_CALL,  # CALL operation
        )

    async def perform_governor_vote(
        self,
        governor_id: str,
        proposal_id: int,
        support: Support,
        reason: str = "",
        chain: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cast a vote on a governor proposal via Safe multisig.

        Args:
            governor_id: Governor identifier (e.g., "compound-mainnet")
            proposal_id: Proposal ID to vote on
            support: Vote choice (FOR, AGAINST, ABSTAIN)
            reason: Optional reason for the vote
            chain: Specific chain to use, or None to use governor's chain

        Returns:
            Dict with transaction details and success status
        """
        # Runtime assertions for critical inputs
        assert isinstance(governor_id, str) and governor_id, "Governor ID must be a non-empty string"
        assert isinstance(proposal_id, int) and proposal_id >= 0, "Proposal ID must be a non-negative integer"
        
        try:
            # Get governor metadata
            governor_meta, _ = get_governor(governor_id)
            
            # Use governor's chain if not specified
            if not chain:
                chain = CHAIN_ID_TO_NAME.get(governor_meta.chain_id)
                if not chain:
                    error_msg = f"Unsupported chain ID: {governor_meta.chain_id}"
                    return {
                        "success": False,
                        "error": error_msg
                    }

            # Encode the vote transaction
            encoded_data = encode_cast_vote(
                governor_id=governor_id,
                proposal_id=proposal_id,
                support=support,
                reason=reason
            )

            # Convert hex string to bytes
            data_bytes = bytes.fromhex(encoded_data[2:])  # Remove '0x' prefix

            # Submit the transaction
            return await self._submit_safe_transaction(
                chain=chain,
                to=governor_meta.address,
                value=0,  # No ETH sent
                data=data_bytes,
                operation=SAFE_OPERATION_CALL,  # CALL operation
            )

        except GovernorRegistryError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            self.logger.error(f"Error creating governor vote transaction: {e}")
            return {"success": False, "error": str(e)}

    async def get_safe_nonce(self, chain: str, safe_address: str) -> int:
        """Get current nonce for a Safe on specified chain.

        Args:
            chain: Blockchain network name
            safe_address: Safe contract address

        Returns:
            Current Safe nonce
        """
        eth_client = EthereumClient(self.rpc_endpoints[chain])  # type: ignore
        safe_instance = Safe(Web3.to_checksum_address(safe_address), eth_client)  # type: ignore
        return safe_instance.retrieve_nonce()

    async def build_safe_transaction(
        self, chain: str, to: str, value: int = 0, data: bytes = b"", operation: int = 0
    ) -> Dict[str, Any]:
        """Build a Safe transaction for execution.

        Args:
            chain: Blockchain network name
            to: Recipient address
            value: ETH value to send
            data: Transaction data
            operation: Safe operation type (0=CALL, 1=DELEGATECALL)

        Returns:
            Dict with transaction details
        """
        safe_address = self.safe_addresses.get(chain)
        if not safe_address:
            raise ValueError(f"No Safe address configured for chain: {chain}")

        safe_address = Web3.to_checksum_address(safe_address)
        eth_client = EthereumClient(self.rpc_endpoints[chain])  # type: ignore
        safe_instance = Safe(safe_address, eth_client)  # type: ignore

        safe_tx = safe_instance.build_multisig_tx(
            to=to,
            value=value,
            data=data,
            operation=operation,
        )

        return {
            "safe_address": safe_address,
            "to": safe_tx.to,
            "value": safe_tx.value,
            "data": safe_tx.data.hex() if safe_tx.data else "",
            "operation": safe_tx.operation,
            "safe_tx_gas": safe_tx.safe_tx_gas,
            "base_gas": safe_tx.base_gas,
            "gas_price": safe_tx.gas_price,
            "gas_token": safe_tx.gas_token,
            "refund_receiver": safe_tx.refund_receiver,
            "nonce": safe_tx.safe_nonce,
            "safe_tx_hash": safe_tx.safe_tx_hash.hex(),
        }
