"""Safe transaction service for handling multi-signature wallet operations."""

import json
from typing import Dict, Optional, Any
from web3 import Web3
from eth_account import Account
from safe_eth.eth import EthereumClient
from safe_eth.safe import Safe
from safe_eth.safe.api import TransactionServiceApi

from config import settings

from models import EASAttestationData

from logging_config import setup_pearl_logger, log_span


# Constants for Safe service URLs
SAFE_SERVICE_URLS = {
    "ethereum": "https://safe-transaction-mainnet.safe.global/",
    "gnosis": "https://safe-transaction-gnosis-chain.safe.global/",
    "base": "https://safe-transaction-base.safe.global/",
    "mode": "https://safe-transaction-mode.safe.global/",
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
        operation: int = SAFE_OPERATION_CALL,
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
        assert (
            isinstance(value, int) and value >= 0
        ), "Value must be a non-negative integer"
        assert isinstance(data, bytes), "Data must be bytes"

        with log_span(
            self.logger, "safe_service._submit_safe_transaction", chain=chain, to=to
        ):
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
                self.logger.info(
                    f"Executed Safe transaction on-chain (tx_hash={tx_hash.hex()})"
                )

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
            return {
                "success": False,
                "error": f"No Safe address configured for chain: {chain}",
            }

        # Use helper method to submit dummy transaction
        return await self._submit_safe_transaction(
            chain=chain,
            to=safe_address,  # Send to itself
            value=0,  # 0 ETH value
            data=b"",  # Empty data
            operation=SAFE_OPERATION_CALL,  # CALL operation
        )



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

    async def create_eas_attestation(
        self, attestation_data: EASAttestationData
    ) -> Dict[str, Any]:
        """Create an EAS attestation for a Snapshot vote.

        Args:
            attestation_data: The attestation data containing vote details

        Returns:
            Dict containing success status and transaction details or error
        """
        try:
            # Check if EAS configuration is available
            if not settings.eas_contract_address or not settings.eas_schema_uid:
                return {
                    "success": False,
                    "error": "EAS configuration missing: contract address or schema UID not set",
                }

            if not settings.base_safe_address:
                return {"success": False, "error": "Base Safe address not configured"}

            # Build the attestation transaction
            tx_data = self._build_eas_attestation_tx(attestation_data)

            # Submit through Safe
            result = await self._submit_safe_transaction(
                chain="base",
                to=tx_data["to"],
                data=tx_data["data"],
                value=tx_data.get("value", 0),
            )

            self.logger.info(
                f"Submitted Safe transaction for attestation. "
                f"Safe tx hash: {result.get('hash')}."
            )

            return {"success": True, "safe_tx_hash": result.get("hash")}

        except Exception as e:
            self.logger.error(f"Failed to create EAS attestation: {str(e)}")
            return {"success": False, "error": str(e)}

    def _build_eas_attestation_tx(
        self, attestation_data: EASAttestationData
    ) -> Dict[str, Any]:
        """Build attestation transaction data.

        Routes to AttestationTracker when configured, otherwise uses direct EAS.
        Both use the delegated attestation pattern for Safe multisig compatibility.

        Args:
            attestation_data: The attestation data to encode

        Returns:
            Transaction data dict with 'to', 'data', and 'value' fields
        """
        # Use AttestationTracker if configured, otherwise direct EAS
        if settings.attestation_tracker_address:
            # Assertion for type checking
            assert settings.attestation_tracker_address is not None
            return self._build_delegated_attestation_tx(
                attestation_data,
                target_address=settings.attestation_tracker_address,
                abi_name="attestation_tracker",
            )
        else:
            # Build delegated request for direct EAS (updating from current attest() pattern)
            if not settings.eas_contract_address:
                raise ValueError("EAS contract address not configured")
            return self._build_delegated_attestation_tx(
                attestation_data,
                target_address=settings.eas_contract_address,
                abi_name="eas",
            )

    def _build_delegated_attestation_tx(
        self, attestation_data: EASAttestationData, target_address: str, abi_name: str
    ) -> Dict[str, Any]:
        """Build delegated attestation transaction.

        Args:
            attestation_data: The attestation data
            target_address: Contract address to call
            abi_name: Name of ABI file to load

        Returns:
            Transaction data dict
        """
        from utils.web3_provider import get_w3
        from utils.abi_loader import load_abi

        w3 = get_w3(settings.attestation_chain)

        # Load ABI using existing utility
        contract_abi = load_abi(abi_name)

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(target_address), abi=contract_abi
        )

        # Build delegated attestation request
        delegated_request = {
            "schema": Web3.to_bytes(hexstr=settings.eas_schema_uid),
            "data": self._encode_attestation_data(attestation_data),
            "expirationTime": 0,
            "revocable": True,
            "refUID": b"\x00" * 32,
            "recipient": Web3.to_checksum_address(attestation_data.voter_address),
            "value": 0,
            "deadline": 0,
            "signature": b"",  # Empty for Safe multisig pattern
        }

        self.logger.info(
            f"Building delegated attestation for {abi_name} at {target_address[:10]}..."
        )

        # Build transaction
        tx = contract.functions.attestByDelegation(delegated_request).build_transaction(
            {
                "from": settings.base_safe_address,
                "gas": 300000,  # Standard gas limit
            }
        )

        return {"to": tx["to"], "data": tx["data"], "value": tx.get("value", 0)}

    def _encode_attestation_data(self, attestation_data: EASAttestationData) -> bytes:
        """Encode attestation data according to EAS schema.

        The schema encodes:
        - proposal_id (string)
        - space_id (string)
        - choice (uint256)
        - vote_tx_hash (bytes32)

        Args:
            attestation_data: The attestation data to encode

        Returns:
            ABI-encoded bytes
        """
        w3 = Web3()

        # Encode the attestation data
        encoded = w3.codec.encode(
            ["string", "string", "uint256", "bytes32"],
            [
                attestation_data.proposal_id,
                attestation_data.space_id,
                attestation_data.choice,
                Web3.to_bytes(hexstr=attestation_data.vote_tx_hash),
            ],
        )

        return encoded

    def _get_web3_instance(self, chain: str) -> Web3:
        """Get Web3 instance for a specific chain.

        Args:
            chain: The chain name (e.g., 'base')

        Returns:
            Web3 instance connected to the chain
        """
        rpc_url = self.rpc_endpoints.get(chain)
        if not rpc_url:
            raise ValueError(f"No RPC endpoint configured for chain: {chain}")

        return Web3(Web3.HTTPProvider(rpc_url))
