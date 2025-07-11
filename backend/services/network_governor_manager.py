"""Network Governor Manager - Multi-network support for governor operations.

This module provides network-aware governor operations including:
- Automatic network detection and governor selection
- RPC endpoint management per network
- Fallback mechanisms for unknown networks
- Network switching and configuration updates
"""

from typing import Any, Dict, List, Optional

from models import (
    GovernorRegistryEntry,
    NetworkGovernorConfig,
    NetworkNotFoundError,
)


class NetworkGovernorManager:
    """Network-aware governor operations with multi-network support."""
    
    def __init__(self):
        """Initialize network governor manager."""
        self.network_configs: Dict[str, NetworkGovernorConfig] = {}
        self.current_network: str = "mainnet"
        self.rpc_endpoints: Dict[str, Dict[str, Any]] = {}
        self.network_governors: Dict[str, List[GovernorRegistryEntry]] = {}
        
        # Setup default networks
        self._setup_default_networks()
    
    def _setup_default_networks(self):
        """Setup default network configurations."""
        # Mainnet configuration
        mainnet_config = NetworkGovernorConfig(
            network_name="mainnet",
            chain_id=1,
            rpc_url="https://mainnet.infura.io/v3/default",
            backup_rpc_urls=[
                "https://eth-mainnet.alchemyapi.io/v2/backup",
                "https://mainnet.infura.io/v3/backup"
            ],
            block_explorer_url="https://etherscan.io",
            is_testnet=False,
            gas_estimation_multiplier=1.2,
            max_fee_per_gas="50000000000",  # 50 gwei
            priority_fee_per_gas="2000000000",  # 2 gwei
        )
        self.network_configs["mainnet"] = mainnet_config
        
        # Goerli testnet configuration
        goerli_config = NetworkGovernorConfig(
            network_name="goerli",
            chain_id=5,
            rpc_url="https://goerli.infura.io/v3/default",
            backup_rpc_urls=["https://goerli.infura.io/v3/backup"],
            block_explorer_url="https://goerli.etherscan.io",
            is_testnet=True,
            gas_estimation_multiplier=1.1,
            max_fee_per_gas="20000000000",  # 20 gwei
            priority_fee_per_gas="1000000000",  # 1 gwei
        )
        self.network_configs["goerli"] = goerli_config
        
        # Setup RPC endpoint mappings
        self._setup_rpc_mappings()
    
    def _setup_rpc_mappings(self):
        """Setup RPC endpoint mappings from network configs."""
        for network_name, config in self.network_configs.items():
            self.rpc_endpoints[network_name] = {
                "primary_rpc": config.rpc_url,
                "backup_rpcs": config.backup_rpc_urls,
                "chain_id": config.chain_id,
                "block_explorer": config.block_explorer_url,
                "gas_multiplier": config.gas_estimation_multiplier,
            }
    
    def add_network_config(self, config: NetworkGovernorConfig):
        """Add new network configuration."""
        self.network_configs[config.network_name] = config
        
        # Update RPC mappings
        self.rpc_endpoints[config.network_name] = {
            "primary_rpc": config.rpc_url,
            "backup_rpcs": config.backup_rpc_urls,
            "chain_id": config.chain_id,
            "block_explorer": config.block_explorer_url,
            "gas_multiplier": config.gas_estimation_multiplier,
        }
    
    def get_network_config(self, network_name: str) -> Optional[NetworkGovernorConfig]:
        """Get network configuration by name."""
        return self.network_configs.get(network_name)
    
    def list_available_networks(self) -> List[str]:
        """List all available networks."""
        return list(self.network_configs.keys())
    
    def detect_network_from_chain_id(self, chain_id: int) -> Optional[str]:
        """Detect network name from chain ID."""
        for network_name, config in self.network_configs.items():
            if config.chain_id == chain_id:
                return network_name
        return None
    
    def switch_network(self, network_name: str):
        """Switch to different network."""
        if network_name not in self.network_configs:
            raise NetworkNotFoundError(network_name)
        
        self.current_network = network_name
    
    def get_current_network(self) -> str:
        """Get current active network."""
        return self.current_network
    
    def get_primary_rpc_endpoint(self, network_name: Optional[str] = None) -> str:
        """Get primary RPC endpoint for network."""
        target_network = network_name or self.current_network
        
        if target_network not in self.rpc_endpoints:
            raise NetworkNotFoundError(target_network)
        
        return self.rpc_endpoints[target_network]["primary_rpc"]
    
    def get_backup_rpc_endpoints(self, network_name: Optional[str] = None) -> List[str]:
        """Get backup RPC endpoints for network."""
        target_network = network_name or self.current_network
        
        if target_network not in self.rpc_endpoints:
            raise NetworkNotFoundError(target_network)
        
        return self.rpc_endpoints[target_network]["backup_rpcs"]
    
    def get_all_rpc_endpoints(self, network_name: Optional[str] = None) -> List[str]:
        """Get all RPC endpoints (primary + backups) for network."""
        target_network = network_name or self.current_network
        
        primary = self.get_primary_rpc_endpoint(target_network)
        backups = self.get_backup_rpc_endpoints(target_network)
        
        return [primary] + backups
    
    def validate_rpc_endpoint(self, rpc_url: str) -> bool:
        """Validate RPC endpoint connectivity."""
        try:
            # Mock validation - in real implementation would test connection
            return rpc_url.startswith("http") and len(rpc_url) > 10
        except Exception:
            return False
    
    def get_working_rpc_endpoint(self, network_name: Optional[str] = None) -> Optional[str]:
        """Get first working RPC endpoint for network."""
        target_network = network_name or self.current_network
        
        all_endpoints = self.get_all_rpc_endpoints(target_network)
        
        for endpoint in all_endpoints:
            if self.validate_rpc_endpoint(endpoint):
                return endpoint
        
        return None
    
    def register_network_governors(self, network_name: str, governors: List[GovernorRegistryEntry]):
        """Register governors for specific network."""
        if network_name not in self.network_configs:
            raise NetworkNotFoundError(network_name)
        
        self.network_governors[network_name] = governors
    
    def get_network_governors(self, network_name: str) -> List[GovernorRegistryEntry]:
        """Get governors available on specific network."""
        return self.network_governors.get(network_name, [])
    
    def find_governor_on_network(
        self, 
        organization_id: str, 
        network_name: Optional[str] = None
    ) -> Optional[GovernorRegistryEntry]:
        """Find governor for organization on specific network."""
        target_network = network_name or self.current_network
        
        network_governors = self.get_network_governors(target_network)
        
        for governor in network_governors:
            if governor.organization_id == organization_id:
                return governor
        
        return None
    
    def get_network_gas_config(self, network_name: Optional[str] = None) -> Dict[str, Any]:
        """Get gas configuration for network."""
        target_network = network_name or self.current_network
        
        if target_network not in self.network_configs:
            raise NetworkNotFoundError(target_network)
        
        config = self.network_configs[target_network]
        
        return {
            "max_fee_per_gas": config.max_fee_per_gas,
            "priority_fee_per_gas": config.priority_fee_per_gas,
            "gas_multiplier": config.gas_estimation_multiplier,
        }
    
    def is_testnet(self, network_name: Optional[str] = None) -> bool:
        """Check if network is a testnet."""
        target_network = network_name or self.current_network
        
        if target_network not in self.network_configs:
            return False
        
        return self.network_configs[target_network].is_testnet
    
    def get_block_explorer_url(self, network_name: Optional[str] = None) -> str:
        """Get block explorer URL for network."""
        target_network = network_name or self.current_network
        
        if target_network not in self.network_configs:
            raise NetworkNotFoundError(target_network)
        
        return self.network_configs[target_network].block_explorer_url
    
    def update_network_rpc_endpoints(self, network_name: str, endpoints: Dict[str, Any]):
        """Update RPC endpoints for network."""
        if network_name not in self.network_configs:
            raise NetworkNotFoundError(network_name)
        
        # Update network config
        config = self.network_configs[network_name]
        if "primary_rpc" in endpoints:
            config.rpc_url = endpoints["primary_rpc"]
        if "backup_rpcs" in endpoints:
            config.backup_rpc_urls = endpoints["backup_rpcs"]
        
        # Update RPC mappings
        self.rpc_endpoints[network_name].update(endpoints)
    
    def get_network_status(self, network_name: Optional[str] = None) -> Dict[str, Any]:
        """Get comprehensive network status."""
        target_network = network_name or self.current_network
        
        if target_network not in self.network_configs:
            raise NetworkNotFoundError(target_network)
        
        config = self.network_configs[target_network]
        
        # Test RPC connectivity
        primary_working = self.validate_rpc_endpoint(config.rpc_url)
        backup_status = [
            self.validate_rpc_endpoint(url) for url in config.backup_rpc_urls
        ]
        
        return {
            "network_name": target_network,
            "chain_id": config.chain_id,
            "is_testnet": config.is_testnet,
            "primary_rpc_working": primary_working,
            "backup_rpcs_working": backup_status,
            "total_endpoints": 1 + len(config.backup_rpc_urls),
            "working_endpoints": [primary_working] + backup_status,
            "governor_count": len(self.get_network_governors(target_network)),
        }
    
    def auto_select_best_network(self, organization_id: str) -> Optional[str]:
        """Automatically select best network for organization."""
        # Check current network first
        if self.find_governor_on_network(organization_id, self.current_network):
            return self.current_network
        
        # Check mainnet
        if self.find_governor_on_network(organization_id, "mainnet"):
            return "mainnet"
        
        # Check other networks
        for network_name in self.network_configs:
            if self.find_governor_on_network(organization_id, network_name):
                return network_name
        
        return None
    
    def get_cross_network_governor_summary(self, organization_id: str) -> Dict[str, Any]:
        """Get governor information across all networks."""
        summary = {
            "organization_id": organization_id,
            "networks": {},
            "total_governors": 0,
            "primary_network": None,
        }
        
        for network_name in self.network_configs:
            governor = self.find_governor_on_network(organization_id, network_name)
            if governor:
                summary["networks"][network_name] = {
                    "governor_id": governor.governor_id,
                    "contract_address": governor.contract_address,
                    "governor_type": governor.governor_type,
                    "is_active": governor.is_active,
                }
                summary["total_governors"] += 1
                
                # Set primary network (prefer mainnet)
                if not summary["primary_network"] or network_name == "mainnet":
                    summary["primary_network"] = network_name
        
        return summary