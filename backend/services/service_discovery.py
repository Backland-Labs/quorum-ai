"""Service discovery utilities for OLAS registry integration."""

from __future__ import annotations

from typing import Optional

from web3 import Web3
from web3.contract import Contract

from logging_config import setup_pearl_logger


# Minimal ServiceRegistry ABI required for discovery operations
# Based on actual ServiceRegistryL2 contract on Base
SERVICE_REGISTRY_ABI = [
    {
        "name": "getService",
        "type": "function",
        "stateMutability": "view",
        "inputs": [{"name": "serviceId", "type": "uint256"}],
        "outputs": [
            {
                "name": "service",
                "type": "tuple",
                "components": [
                    {"name": "securityDeposit", "type": "uint96"},
                    {"name": "multisig", "type": "address"},
                    {"name": "configHash", "type": "bytes32"},
                    {"name": "threshold", "type": "uint32"},
                    {"name": "maxNumAgentInstances", "type": "uint32"},
                    {"name": "numAgentInstances", "type": "uint32"},
                    {"name": "state", "type": "uint8"},
                    {"name": "agentIds", "type": "uint32[]"},
                ],
            }
        ],
    },
    {
        "name": "totalSupply",
        "type": "function",
        "stateMutability": "view",
        "inputs": [],
        "outputs": [{"name": "", "type": "uint256"}],
    },
]


class ServiceDiscovery:
    """Encapsulates logic for discovering OLAS service IDs."""

    def __init__(self, service_registry_address: str, rpc_url: str) -> None:
        assert rpc_url, "RPC URL is required for service discovery"
        self.logger = setup_pearl_logger(__name__)
        self.rpc_url = rpc_url
        self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self.registry: Contract = self.web3.eth.contract(
            address=service_registry_address,
            abi=SERVICE_REGISTRY_ABI,
        )

    def get_service_id_from_safe_address(self, safe_address: str) -> Optional[int]:
        """Search ServiceRegistry for a service matching the provided Safe address."""

        assert safe_address, "Safe address is required for service discovery"

        try:
            # Test RPC connection first
            try:
                block_number = self.web3.eth.block_number
                chain_id = self.web3.eth.chain_id
                self.logger.debug(
                    f"RPC connection verified, block_number={block_number}, "
                    f"chain_id={chain_id}, rpc_url={self.rpc_url}"
                )
            except Exception as rpc_error:
                self.logger.warning(
                    f"RPC connection failed: {rpc_error}, rpc_url={self.rpc_url}"
                )
                raise RuntimeError(
                    f"Cannot connect to RPC endpoint {self.rpc_url}: {rpc_error}"
                ) from rpc_error

            # Check if contract exists by checking bytecode
            try:
                code = self.web3.eth.get_code(self.registry.address)
                code_len = len(code) if code else 0
                self.logger.debug(
                    f"Checking contract existence: registry={self.registry.address}, "
                    f"code_len={code_len}"
                )
                if code == b"" or code == "0x" or code_len == 0:
                    self.logger.info(
                        f"ServiceRegistry contract not found at {self.registry.address} on {self.rpc_url} (chain_id={chain_id}). "
                        f"Service discovery skipped. This is expected in fork/local development environments."
                    )
                    return None
            except Exception as code_check_error:
                self.logger.debug(
                    f"Failed to check contract code: {code_check_error}, "
                    f"registry_address={self.registry.address}"
                )

            # Call totalSupply with better error handling
            try:
                total_services = self.registry.functions.totalSupply().call()
                self.logger.info(
                    f"Discovering service ID from ServiceRegistry "
                    f"total_services={total_services}, "
                    f"registry_address={self.registry.address}"
                )
            except Exception as total_supply_error:
                self.logger.warning(
                    f"Failed to call totalSupply on ServiceRegistry: {total_supply_error}, "
                    f"registry_address={self.registry.address}, "
                    f"rpc_url={self.rpc_url}"
                )
                raise RuntimeError(
                    f"ServiceRegistry.totalSupply() call failed at {self.registry.address}. "
                    f"Verify the contract exists on this network and the address is correct. "
                    f"Error: {total_supply_error}"
                ) from total_supply_error

            # Iterate through services (include total_services since service IDs may be 1-indexed)
            for service_id in range(total_services + 1):
                try:
                    service_info = self.registry.functions.getService(service_id).call()
                    multisig_address = service_info[1]

                    if (
                        multisig_address
                        and multisig_address.lower() == safe_address.lower()
                    ):
                        self.logger.info(
                            f"Found service ID for Safe "
                            f"service_id={service_id}, "
                            f"safe={safe_address}"
                        )
                        return service_id
                except Exception as get_service_error:
                    self.logger.warning(
                        f"Failed to query service_id={service_id}: {get_service_error}"
                    )
                    continue

            self.logger.warning(
                f"No service ID found for Safe "
                f"safe={safe_address}, "
                f"total_services_checked={total_services}"
            )
            return None

        except RuntimeError:
            # Re-raise RuntimeError with context
            raise
        except (ConnectionError, TimeoutError, ValueError) as e:
            # Catch specific expected exceptions
            self.logger.error(
                "Service discovery error: %s, safe=%s, registry=%s, rpc=%s",
                e,
                safe_address,
                self.registry.address,
                self.rpc_url,
            )
            raise RuntimeError(f"Service discovery failed: {e}") from e
