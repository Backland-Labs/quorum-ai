"""Governor Configuration Manager - Configuration loading and management.

This module provides configuration management functionality including:
- Environment variable parsing with hierarchy
- JSON file configuration loading  
- Hot reloading capabilities
- Configuration validation with detailed error reporting
"""

import json
import os
from typing import Any, Dict, List

from models import (
    ConfigurationValidationError,
    ConfigurationSchemaError,
)


class GovernorConfigManager:
    """Configuration loading and management with hierarchy support."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self.config_sources: List[str] = []
        self.config_cache: Dict[str, Any] = {}
        self.hot_reload_enabled: bool = True
        
    def load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config = {
            "governors": {},
            "networks": {},
            "settings": {}
        }
        
        # Parse governor registry variables
        for key, value in os.environ.items():
            if key.startswith("GOVERNOR_REGISTRY_"):
                parts = key.split("_")
                if len(parts) >= 3:
                    dao_name = "_".join(parts[2:])
                    dao_id = dao_name.lower().replace("_", "-")
                    
                    config["governors"][dao_id] = {
                        "contract_address": value,
                        "governor_type": os.getenv(f"GOVERNOR_REGISTRY_{dao_name}_TYPE", "CustomGovernor"),
                        "network": os.getenv(f"GOVERNOR_REGISTRY_{dao_name}_NETWORK", "mainnet"),
                        "organization_id": dao_id,
                    }
        
        # Parse network configurations
        for network in ["mainnet", "goerli", "polygon", "arbitrum"]:
            rpc_key = f"{network.upper()}_RPC_URL"
            if rpc_key in os.environ:
                config["networks"][network] = {
                    "rpc_url": os.environ[rpc_key],
                    "chain_id": self._get_chain_id(network),
                }
        
        return config
    
    def _get_chain_id(self, network: str) -> int:
        """Get chain ID for network."""
        chain_ids = {
            "mainnet": 1,
            "goerli": 5,
            "polygon": 137,
            "arbitrum": 42161,
        }
        return chain_ids.get(network, 1)
    
    def load_from_json_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationValidationError(f"Invalid JSON in file {file_path}: {e}")
        except FileNotFoundError:
            raise ConfigurationValidationError(f"Configuration file not found: {file_path}")
        except Exception as e:
            raise ConfigurationValidationError(f"Error reading configuration file: {e}")
    
    def validate_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration and return validation results."""
        results = {
            "is_valid": True,
            "errors": [],
            "warnings": []
        }
        
        # Validate governors section
        if "governors" in config:
            for governor_id, governor_config in config["governors"].items():
                errors = self._validate_governor_config(governor_id, governor_config)
                results["errors"].extend(errors)
        
        # Validate networks section
        if "networks" in config:
            for network_name, network_config in config["networks"].items():
                errors = self._validate_network_config(network_name, network_config)
                results["errors"].extend(errors)
        
        results["is_valid"] = len(results["errors"]) == 0
        return results
    
    def _validate_governor_config(self, governor_id: str, config: Dict[str, Any]) -> List[str]:
        """Validate individual governor configuration."""
        errors = []
        
        # Required fields
        required_fields = ["contract_address", "governor_type", "network"]
        for field in required_fields:
            if field not in config:
                errors.append(f"Governor {governor_id}: missing required field '{field}'")
            elif not config[field]:
                errors.append(f"Governor {governor_id}: empty value for required field '{field}'")
        
        # Validate address format
        if "contract_address" in config:
            address = config["contract_address"]
            if not self._is_valid_ethereum_address(address):
                errors.append(f"Governor {governor_id}: invalid contract address '{address}'")
        
        # Validate network
        if "network" in config:
            network = config["network"]
            if network not in ["mainnet", "goerli", "polygon", "arbitrum"]:
                errors.append(f"Governor {governor_id}: unknown network '{network}'")
        
        return errors
    
    def _validate_network_config(self, network_name: str, config: Dict[str, Any]) -> List[str]:
        """Validate network configuration."""
        errors = []
        
        # Check required fields
        if "rpc_url" not in config:
            errors.append(f"Network {network_name}: missing rpc_url")
        
        if "chain_id" not in config:
            errors.append(f"Network {network_name}: missing chain_id")
        elif not isinstance(config["chain_id"], int):
            errors.append(f"Network {network_name}: chain_id must be integer")
        
        return errors
    
    def _is_valid_ethereum_address(self, address: str) -> bool:
        """Validate Ethereum address format."""
        if not isinstance(address, str):
            return False
        
        if not address.startswith("0x"):
            return False
        
        if len(address) != 42:
            return False
        
        try:
            int(address[2:], 16)
            return True
        except ValueError:
            return False
    
    def merge_configurations(self, configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge multiple configurations with priority order."""
        merged = {}
        
        for config in configs:
            merged = self._deep_merge(merged, config)
        
        return merged
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def enable_hot_reload(self, enabled: bool = True):
        """Enable or disable hot reloading."""
        self.hot_reload_enabled = enabled
    
    def reload_configuration(self, file_path: str) -> Dict[str, Any]:
        """Hot reload configuration from file."""
        if not self.hot_reload_enabled:
            raise ConfigurationValidationError("Hot reload is disabled")
        
        return self.load_from_json_file(file_path)
    
    def get_configuration_hierarchy(self) -> List[str]:
        """Get configuration source hierarchy."""
        return [
            "environment_variables",
            "config_files", 
            "remote_urls",
            "defaults"
        ]
    
    def parse_configuration_string(self, config_string: str, format_type: str = "json") -> Dict[str, Any]:
        """Parse configuration from string."""
        if format_type == "json":
            try:
                return json.loads(config_string)
            except json.JSONDecodeError as e:
                raise ConfigurationValidationError(f"Invalid JSON configuration: {e}")
        else:
            raise ConfigurationValidationError(f"Unsupported configuration format: {format_type}")
    
    def export_configuration(self, config: Dict[str, Any], file_path: str):
        """Export configuration to file."""
        try:
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            raise ConfigurationValidationError(f"Error exporting configuration: {e}")
    
    def get_default_configuration(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "version": "1.0",
            "governors": {
                "compound-bravo": {
                    "contract_address": "0xc0Da02939E1441F497fd74F78cE7Decb17B66529",
                    "governor_type": "CompoundBravoGovernor",
                    "network": "mainnet",
                    "organization_id": "compound",
                },
            },
            "networks": {
                "mainnet": {
                    "chain_id": 1,
                    "rpc_url": "https://mainnet.infura.io/v3/...",
                    "block_explorer": "https://etherscan.io",
                },
            },
            "settings": {
                "cache_ttl": 3600,
                "hot_reload_enabled": True,
            }
        }
    
    def validate_schema(self, config: Dict[str, Any]) -> bool:
        """Validate configuration schema."""
        try:
            # Basic schema validation
            if not isinstance(config, dict):
                raise ConfigurationSchemaError("Configuration must be a dictionary")
            
            # Check for required top-level sections
            if "governors" not in config:
                raise ConfigurationSchemaError("Missing 'governors' section")
            
            if not isinstance(config["governors"], dict):
                raise ConfigurationSchemaError("'governors' section must be a dictionary")
            
            # Validate each governor entry
            for governor_id, governor_config in config["governors"].items():
                if not isinstance(governor_config, dict):
                    raise ConfigurationSchemaError(f"Governor '{governor_id}' must be a dictionary")
                
                required_fields = ["contract_address", "governor_type", "network"]
                for field in required_fields:
                    if field not in governor_config:
                        raise ConfigurationSchemaError(f"Governor '{governor_id}' missing required field '{field}'")
            
            return True
            
        except ConfigurationSchemaError:
            raise
        except Exception as e:
            raise ConfigurationSchemaError(f"Schema validation error: {e}")