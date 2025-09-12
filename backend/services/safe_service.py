"""Safe transaction service for handling multi-signature wallet operations."""

import json
import time
from typing import Dict, Optional, Any, List
from web3 import Web3
from eth_account import Account
from safe_eth.eth import EthereumClient
from safe_eth.safe import Safe
from safe_eth.safe.api import TransactionServiceApi

from config import settings

from models import EASAttestationData
from utils.eas_signature import generate_eas_delegated_signature

from logging_config import setup_pearl_logger, log_span

# Constants for Safe service URLs
SAFE_SERVICE_URLS = {
    "ethereum": "https://safe-transaction-mainnet.safe.global/",
    "gnosis": "https://safe-transaction-gnosis-chain.safe.global/",
    "base": "https://safe-transaction-base.safe.global/",
    "mode": "https://safe-transaction-mode.safe.global/",
}

# Gas limit for EAS attestation transactions
# Increased from 300,000 to handle complex nested calls through AttestationTracker to EAS
EAS_ATTESTATION_GAS_LIMIT = 1000000


# Safe operation types
SAFE_OPERATION_CALL = 0
SAFE_OPERATION_DELEGATECALL = 1


class SafeService:
    """Service for handling Safe multi-signature wallet transactions.

    Supports transactions on chains that have:
    1. Safe contract address configured in SAFE_CONTRACT_ADDRESSES
    2. RPC endpoint configured
    3. Safe Transaction Service API available

    Currently supported chains: ethereum, gnosis, base, mode

    Use get_supported_chains() to check which chains are available in your configuration.
    """

    def __init__(self):
        """Initialize Safe service with configuration."""
        # Validate configuration early in initialization
        if not settings.get_base_rpc_endpoint():
            raise RuntimeError(f"Safe service is disabled in configuration: enable_safe_service={settings.get_base_rpc_endpoint()}")
        
        assert settings.get_base_rpc_endpoint() is not None, "Base RPC endpoint must be set"
        
        self.logger = setup_pearl_logger(__name__)
        self.safe_addresses = json.loads(settings.safe_contract_addresses)
        self.rpc_endpoints = {
            "ethereum": settings.ethereum_ledger_rpc,
            "gnosis": settings.gnosis_ledger_rpc,
            "base": settings.get_base_rpc_endpoint(),
            "mode": settings.mode_ledger_rpc,
        }

        # Initialize account from private key
        with open("ethereum_private_key.txt", "r") as f:
            private_key = f.read().strip()

        self.private_key = private_key
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

    def is_chain_fully_configured(self, chain: str) -> bool:
        """Check if a chain has all required configuration for Safe transactions.
        
        Args:
            chain: Chain name to validate
            
        Returns:
            True if chain has Safe address, RPC endpoint, and Safe service URL
        """
        has_safe_address = (
            chain in self.safe_addresses 
            and self.safe_addresses[chain]
        )
        has_rpc_endpoint = (
            chain in self.rpc_endpoints 
            and self.rpc_endpoints[chain]
        )
        has_safe_service = chain in SAFE_SERVICE_URLS
        
        return has_safe_address and has_rpc_endpoint and has_safe_service

    def get_supported_chains(self) -> List[str]:
        """Get list of chains that are fully configured for Safe transactions.
        
        Returns:
            List of chain names with complete configuration
        """
        return [
            chain for chain in SAFE_SERVICE_URLS.keys()
            if self.is_chain_fully_configured(chain)
        ]

    def validate_chain_configuration(self, chain: str) -> Dict[str, Any]:
        """Validate chain configuration and return detailed status.
        
        Args:
            chain: Chain name to validate
            
        Returns:
            Dict with validation details including what's missing
        """
        return {
            "chain": chain,
            "has_safe_address": chain in self.safe_addresses and bool(self.safe_addresses[chain]),
            "has_rpc_endpoint": chain in self.rpc_endpoints and bool(self.rpc_endpoints[chain]),
            "has_safe_service_url": chain in SAFE_SERVICE_URLS,
            "is_fully_configured": self.is_chain_fully_configured(chain),
            "safe_address": self.safe_addresses.get(chain),
            "rpc_endpoint": self.rpc_endpoints.get(chain),
            "safe_service_url": SAFE_SERVICE_URLS.get(chain),
        }

    def _rate_limit_base_rpc(self, rpc_url: str) -> None:
        """Add rate limiting delay for Base mainnet RPC calls to prevent 429 errors.
        
        Args:
            rpc_url: The RPC endpoint URL to check
        """
        if "mainnet.base.org" in rpc_url:
            self.logger.debug(f"Adding 1-second delay for Base mainnet RPC call to {rpc_url}")
            time.sleep(1.0)

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

        # Add rate limiting for Base mainnet RPC calls
        self._rate_limit_base_rpc(rpc_url)

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
        # Note: Only include chains that have Safe service URLs
        chain_priority = ["gnosis", "mode", "base", "ethereum"]

        for chain in chain_priority:
            if self.is_chain_fully_configured(chain):
                return chain

        # Fallback to first available fully configured chain
        available_chains = self.get_supported_chains()

        if available_chains:
            return available_chains[0]

        # Provide helpful error with list of what's needed
        error_msg = (
            "No valid chain configuration found. "
            "Ensure at least one chain has: Safe address in SAFE_CONTRACT_ADDRESSES, "
            "RPC endpoint configured, and is supported by Safe Transaction Service "
            f"(supported chains: {', '.join(SAFE_SERVICE_URLS.keys())})"
        )
        raise ValueError(error_msg)

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

        # Validate chain is fully configured
        if not self.is_chain_fully_configured(chain):
            validation = self.validate_chain_configuration(chain)
            supported_chains = self.get_supported_chains()
            
            missing_components = []
            if not validation["has_safe_address"]:
                missing_components.append("Safe contract address")
            if not validation["has_rpc_endpoint"]:
                missing_components.append("RPC endpoint")
            if not validation["has_safe_service_url"]:
                missing_components.append("Safe Transaction Service URL")
            
            error_msg = (
                f"Chain '{chain}' is not fully configured for Safe transactions. "
                f"Missing: {', '.join(missing_components)}. "
                f"Supported chains: {', '.join(supported_chains)}"
            )
            
            self.logger.error(error_msg)
            return {"success": False, "error": error_msg}

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
                
                # Add rate limiting before creating EthereumClient
                rpc_url = self.rpc_endpoints[chain]
                self._rate_limit_base_rpc(rpc_url)
                eth_client = EthereumClient(rpc_url)  # type: ignore

                # Initialize Safe instance
                safe_instance = Safe(safe_address, eth_client)  # type: ignore

                # Get Safe service for this chain (validation already done upfront)
                safe_service_url = SAFE_SERVICE_URLS[chain]
                safe_service = TransactionServiceApi(
                    network=chain,  # type: ignore
                    base_url=safe_service_url,
                )

                # Build Safe transaction with proper gas estimation
                safe_tx = safe_instance.build_multisig_tx(
                    to=to,
                    value=value,
                    data=data,
                    operation=operation,
                    safe_tx_gas=100000,  # Set reasonable gas limit to avoid GS013
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

                # Simulate transaction before execution to catch revert reasons
                try:
                    self.logger.info("Simulating Safe transaction before execution")
                    safe_tx.call()  # This will reveal the specific revert reason if transaction would fail
                    self.logger.info("Transaction simulation successful")
                except Exception as simulation_error:
                    self.logger.error(f"Transaction simulation failed: {str(simulation_error)}")
                    return {
                        "success": False, 
                        "error": f"Transaction would revert: {str(simulation_error)}",
                        "simulation_failed": True
                    }

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
                    tx_sender_private_key=self.private_key,
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
                    self.logger.exception(f"Transaction reverted (tx_hash={tx_hash_hex})")
                    return {
                        "success": False,
                        "error": "Transaction reverted",
                        "tx_hash": tx_hash_hex,
                    }

            except Exception as e:
                self.logger.exception(f"Error creating Safe transaction: {str(e)}")

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
        self.logger.info("Performing activity transaction")
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
        # Add rate limiting for Base mainnet RPC calls
        rpc_url = self.rpc_endpoints[chain]
        self._rate_limit_base_rpc(rpc_url)
        
        eth_client = EthereumClient(rpc_url)  # type: ignore
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
        
        # Add rate limiting for Base mainnet RPC calls
        rpc_url = self.rpc_endpoints[chain]
        self._rate_limit_base_rpc(rpc_url)
        
        eth_client = EthereumClient(rpc_url)  # type: ignore
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
            self.logger.info(
                f"Creating EAS attestation (proposal_id={attestation_data.proposal_id}, "
                f"space_id={attestation_data.space_id}, vote_choice={attestation_data.vote_choice}, "
                f"agent={attestation_data.agent})"
            )
            
            # Check if EAS configuration is available
            if not settings.eas_contract_address or not settings.eas_schema_uid:
                self.logger.error(
                    f"EAS configuration missing - contract_address={settings.eas_contract_address}, "
                    f"schema_uid={settings.eas_schema_uid}"
                )
                return {
                    "success": False,
                    "error": "EAS configuration missing: contract address or schema UID not set",
                }

            if not settings.base_safe_address:
                self.logger.error(f"Base Safe address not configured")
                return {"success": False, "error": "Base Safe address not configured"}

            self.logger.info(
                f"EAS configuration validated - contract_address={settings.eas_contract_address}, "
                f"schema_uid={settings.eas_schema_uid}, safe_address={settings.base_safe_address}"
            )

            # Build the attestation transaction
            self.logger.debug("Building EAS attestation transaction data")
            tx_data = self._build_eas_attestation_tx(attestation_data)

            self.logger.info(
                f"Built EAS transaction data - to={tx_data['to']}, "
                f"data_length={len(tx_data['data'])}, value={tx_data.get('value', 0)}"
            )

            # Convert hex string to bytes for Safe transaction
            tx_data_bytes = bytes.fromhex(tx_data["data"][2:]) if tx_data["data"].startswith("0x") else bytes.fromhex(tx_data["data"])

            self.logger.debug(f"Converted transaction data to bytes, length={len(tx_data_bytes)}")

            # Submit through Safe
            self.logger.info("Submitting EAS attestation transaction through Safe")
            result = await self._submit_safe_transaction(
                chain="base",
                to=tx_data["to"],
                data=tx_data_bytes,
                value=tx_data.get("value", 0),
            )

            if result.get("success"):
                self.logger.info(
                    f"EAS attestation transaction submitted successfully - "
                    f"tx_hash={result.get('tx_hash')}, safe_address={result.get('safe_address')}"
                )
            else:
                self.logger.error(
                    f"EAS attestation transaction failed - error={result.get('error')}"
                )

            return {"success": result.get("success", False), "safe_tx_hash": result.get("tx_hash")}

        except Exception as e:
            self.logger.exception(
                f"Failed to create EAS attestation - proposal_id={attestation_data.proposal_id}, "
                f"error={str(e)}"
            )
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
        self.logger.info(
            f"Building EAS attestation transaction - attestation_tracker_address={settings.attestation_tracker_address}, "
            f"eas_contract_address={settings.eas_contract_address}"
        )
        
        # Use AttestationTracker if configured, otherwise direct EAS
        if settings.attestation_tracker_address:
            # Assertion for type checking
            assert settings.attestation_tracker_address is not None
            self.logger.info(
                f"Using AttestationTracker contract for EAS attestation - "
                f"tracker_address={settings.attestation_tracker_address}"
            )
            return self._build_delegated_attestation_tx(
                attestation_data,
                target_address=settings.attestation_tracker_address,
                abi_name="attestation_tracker",
            )
        else:
            if not settings.eas_contract_address:
                self.logger.error("EAS contract address not configured for direct EAS call")
                raise ValueError("EAS contract address not configured")
            
            self.logger.info(
                f"Using EIP712Proxy contract for attestation - "
                f"proxy_address={settings.eas_contract_address}"
            )
            return self._build_delegated_attestation_tx(
                attestation_data,
                target_address=settings.eas_contract_address,
                abi_name="eip712proxy",
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
        self.logger.info(
            f"Building delegated attestation transaction - target_address={target_address}, "
            f"abi_name={abi_name}, attestation_chain={settings.attestation_chain}"
        )
        
        from utils.web3_provider import get_w3
        from utils.abi_loader import load_abi

        # Get Web3 connection
        self.logger.debug(f"Getting Web3 connection for chain: {settings.attestation_chain}")
        w3 = get_w3(settings.attestation_chain)
        current_block = w3.eth.get_block('latest')
        self.logger.debug(f"Current block number: {current_block['number']}, timestamp: {current_block['timestamp']}")

        # Load ABI using existing utility
        self.logger.debug(f"Loading ABI for contract type: {abi_name}")
        contract_abi = load_abi(abi_name)
        self.logger.debug(f"Loaded ABI with {len(contract_abi)} functions/events")

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(target_address), abi=contract_abi
        )
        self.logger.info(f"Created contract instance at address: {target_address}")

        eas_schema_uid = Web3.to_bytes(hexstr=settings.eas_schema_uid)
        assert isinstance(eas_schema_uid, bytes), f"eas_schema_uid must be bytes, got {type(eas_schema_uid)}"
        
        self.logger.debug(f"EAS schema UID: {settings.eas_schema_uid} (as bytes: {eas_schema_uid.hex()})")

        # Encode attestation data
        self.logger.debug("Encoding attestation data")
        encoded_data = self._encode_attestation_data(attestation_data)
        self.logger.debug(f"Encoded attestation data length: {len(encoded_data)} bytes")

        # Build delegated attestation request with proper signature
        deadline = int(current_block['timestamp']) + 3600  # 1 hour deadline
        attestation_request_data = {
            "schema": eas_schema_uid,
            "data": encoded_data,
            "expirationTime": 0,
            "revocable": True,
            "refUID": b"\x00" * 32,
            "recipient": Web3.to_checksum_address(attestation_data.agent),
            "value": 0,
            "deadline": deadline,
        }
        
        self.logger.info(
            f"Built attestation request data - schema={settings.eas_schema_uid}, "
            f"recipient={attestation_data.agent}, deadline={deadline}, "
            f"data_length={len(encoded_data)}"
        )
        
        # Generate EAS delegated signature (always sign for EAS contract, not wrapper)
        eas_address = settings.eas_contract_address
        if not eas_address:
            self.logger.error("EAS contract address not configured for signature generation")
            raise ValueError("EAS contract address not configured")
        
        self.logger.debug(f"Generating EAS delegated signature for EAS contract: {eas_address}")
        signature = self._generate_eas_delegated_signature(
            attestation_request_data, 
            w3, 
            eas_address
        )
        
        # For AttestationTracker, we need to use the new interface with 12 separate parameters
        if abi_name == "attestation_tracker":
            # Parse signature bytes into v, r, s components
            v = signature[64]
            r = signature[:32]
            s = signature[32:64]
            
            # Get attester address from private key
            from eth_account import Account
            import os
            # Load private key from file or env
            private_key = None
            if os.path.exists("ethereum_private_key.txt"):
                with open("ethereum_private_key.txt", "r") as f:
                    private_key = f.read().strip()
            elif os.getenv("ETHEREUM_PRIVATE_KEY"):
                private_key = os.getenv("ETHEREUM_PRIVATE_KEY")
            else:
                raise ValueError("Private key not found in file or environment")
            
            attester = Account.from_key(private_key).address
            
            self.logger.info(
                f"Built delegated request for AttestationTracker with 12 params - attester={attester}, deadline={deadline}"
            )
            
            # Build transaction with 12 separate parameters
            self.logger.debug("Building attestByDelegation transaction with 12-parameter interface")
            tx = contract.functions.attestByDelegation(
                eas_schema_uid,  # schema
                attestation_request_data["recipient"],  # recipient
                attestation_request_data["expirationTime"],  # expirationTime
                attestation_request_data["revocable"],  # revocable
                attestation_request_data["refUID"],  # refUID
                attestation_request_data["data"],  # data
                attestation_request_data["value"],  # value
                v,  # v
                r,  # r
                s,  # s
                attester,  # attester
                deadline  # deadline
            ).build_transaction(
                {
                    "from": settings.base_safe_address,
                    "gas": EAS_ATTESTATION_GAS_LIMIT,
                }
            )
        else:
            # For EIP712Proxy, parse signature and include attester
            v = signature[64]
            r = signature[:32]
            s = signature[32:64]
            
            # Get attester address from private key
            from eth_account import Account
            import os
            private_key = None
            if os.path.exists("ethereum_private_key.txt"):
                with open("ethereum_private_key.txt", "r") as f:
                    private_key = f.read().strip()
            elif os.getenv("ETHEREUM_PRIVATE_KEY"):
                private_key = os.getenv("ETHEREUM_PRIVATE_KEY")
            else:
                raise ValueError("Private key not found in file or environment")
            
            attester = Account.from_key(private_key).address
            
            # Build delegated request for EIP712Proxy with nested structure
            delegated_request = {
                "schema": attestation_request_data["schema"],
                "data": {
                    "recipient": attestation_request_data["recipient"],
                    "expirationTime": attestation_request_data["expirationTime"],
                    "revocable": attestation_request_data["revocable"],
                    "refUID": attestation_request_data["refUID"],
                    "data": attestation_request_data["data"],
                    "value": attestation_request_data["value"],
                },
                "signature": {
                    "v": v,
                    "r": r,
                    "s": s,
                },
                "attester": attester,
                "deadline": attestation_request_data["deadline"],
            }

            self.logger.info(
                f"Built complete delegated request for {abi_name} contract at {target_address} with attester={attester}"
            )

            # Build transaction
            self.logger.debug("Building attestByDelegation transaction")
            tx = contract.functions.attestByDelegation(delegated_request).build_transaction(
                {
                    "from": settings.base_safe_address,
                    "gas": EAS_ATTESTATION_GAS_LIMIT,
                }
            )

        self.logger.info(
            f"Built delegated attestation transaction - to={tx['to']}, "
            f"data_length={len(tx['data'])}, gas={tx.get('gas', 'N/A')}"
        )

        return {"to": tx["to"], "data": tx["data"], "value": tx.get("value", 0)}

    def _encode_attestation_data(self, attestation_data: EASAttestationData) -> bytes:
        """Encode attestation data according to EAS schema.

        The schema encodes:
        - agent (address)
        - space_id (string) 
        - proposal_id (string)
        - vote_choice (uint8)
        - snapshot_sig (string)
        - timestamp (uint256)
        - run_id (string)
        - confidence (uint8)

        Args:
            attestation_data: The attestation data to encode

        Returns:
            ABI-encoded bytes
        """
        w3 = Web3()

        # Ensure agent address is checksummed
        agent_address = Web3.to_checksum_address(attestation_data.agent)
        
        # Encode the attestation data with new schema
        encoded = w3.codec.encode(
            ["address", "string", "string", "uint8", "string", "uint256", "string", "uint8"],
            [
                agent_address,
                attestation_data.space_id,
                attestation_data.proposal_id,
                attestation_data.vote_choice,
                attestation_data.snapshot_sig,
                attestation_data.timestamp,
                attestation_data.run_id,
                attestation_data.confidence,
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

        # Add rate limiting for Base mainnet RPC calls
        self._rate_limit_base_rpc(rpc_url)
        
        return Web3(Web3.HTTPProvider(rpc_url))

    def _generate_eas_delegated_signature(
        self, request_data: Dict[str, Any], w3: Web3, eas_contract_address: str
    ) -> bytes:
        """Generate EIP-712 signature for EAS delegated attestation.
        
        This method now delegates to the shared utility function to ensure
        consistency between SafeService and test scripts.
        
        Args:
            request_data: The attestation request data (without signature)
            w3: Web3 instance
            eas_contract_address: EAS contract address
            
        Returns:
            EIP-712 signature bytes
        """
        self.logger.info(
            f"Generating EAS delegated signature - chain_id={w3.eth.chain_id}, "
            f"eas_contract={eas_contract_address}, signer={self.account.address}"
        )
        
        self.logger.debug(
            f"EIP-712 message - schema={request_data['schema'].hex()}, "
            f"recipient={request_data['recipient']}, deadline={request_data['deadline']}, "
            f"data_length={len(request_data['data'])}"
        )
        
        # Use the shared signature generation function
        # Pass the private key from the loaded file
        with open("ethereum_private_key.txt", "r") as f:
            private_key = f.read().strip()
        
        signature = generate_eas_delegated_signature(
            request_data=request_data,
            w3=w3,
            eas_contract_address=eas_contract_address,
            private_key=private_key
        )
        
        self.logger.info(
            f"Generated EAS delegated signature successfully - signature_length={len(signature)}, "
            f"signature_hex={signature.hex()[:20]}..."
        )
        
        return signature
