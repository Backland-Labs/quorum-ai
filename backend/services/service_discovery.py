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

        total_services = self.registry.functions.totalSupply().call()
        self.logger.info(
            f"Discovering service ID from ServiceRegistry total_services={total_services}"
        )

        for service_id in range(total_services):
            service_info = self.registry.functions.getService(service_id).call()
            multisig_address = service_info[1]

            if multisig_address and multisig_address.lower() == safe_address.lower():
                self.logger.info(
                    f"Found service ID for Safe service_id={service_id} safe={safe_address}"
                )
                return service_id

        self.logger.warning(f"No service ID found for Safe safe={safe_address}")
        return None
