"""TDD Cycle 5 - RED Phase: Comprehensive tests for Governor Registry and Configuration System.

This test suite defines the complete interface and behavior for a dynamic governor registry
that supports runtime registration, organization mapping, multi-network configuration,
and hot reloading of governor contracts and settings.
"""

import json
import os
import tempfile
import threading
import time
from unittest.mock import patch

import pytest
from pydantic import ValidationError



class TestGovernorRegistryModels:
    """Test core registry data models and validation."""

    def test_governor_registry_entry_creation(self):
        """Test creating a governor registry entry with all required fields."""
        # This will fail - GovernorRegistryEntry model doesn't exist yet
        from models import GovernorRegistryEntry

        entry = GovernorRegistryEntry(
            governor_id="compound-bravo",
            contract_address="0xc0Da02939E1441F497fd74F78cE7Decb17B66529",
            governor_type="CompoundBravoGovernor",
            network="mainnet",
            organization_id="compound",
            abi_version="2.0",
            deployment_block=12345678,
            is_active=True,
        )

        assert entry.governor_id == "compound-bravo"
        assert entry.contract_address == "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"
        assert entry.governor_type == "CompoundBravoGovernor"
        assert entry.network == "mainnet"
        assert entry.organization_id == "compound"
        assert entry.abi_version == "2.0"
        assert entry.deployment_block == 12345678
        assert entry.is_active is True

    def test_governor_registry_entry_address_validation(self):
        """Test governor registry entry validates Ethereum addresses."""
        from models import GovernorRegistryEntry

        # Valid address should pass
        entry = GovernorRegistryEntry(
            governor_id="test-governor",
            contract_address="0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234",
            governor_type="TestGovernor",
            network="mainnet",
            organization_id="test-org",
        )
        assert entry.contract_address == "0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234"

        # Invalid address should fail
        with pytest.raises(ValidationError):
            GovernorRegistryEntry(
                governor_id="test-governor",
                contract_address="invalid-address",
                governor_type="TestGovernor",
                network="mainnet",
                organization_id="test-org",
            )

    def test_organization_governor_mapping_creation(self):
        """Test organization to governor mapping model."""
        from models import OrganizationGovernorMapping

        mapping = OrganizationGovernorMapping(
            organization_id="compound",
            organization_name="Compound",
            governor_entries=[
                {
                    "governor_id": "compound-bravo",
                    "contract_address": "0xc0Da02939E1441F497fd74F78cE7Decb17B66529",
                    "governor_type": "CompoundBravoGovernor",
                    "network": "mainnet",
                    "is_primary": True,
                },
                {
                    "governor_id": "compound-alpha",
                    "contract_address": "0x315d9C2E24C47fC8F2bc21C18D26B4e4A37be5c5",
                    "governor_type": "CompoundGovernor",
                    "network": "mainnet",
                    "is_primary": False,
                },
            ],
            metadata={
                "description": "Compound Finance DAO",
                "website": "https://compound.finance",
                "governance_forum": "https://compound.finance/governance",
            },
        )

        assert mapping.organization_id == "compound"
        assert mapping.organization_name == "Compound"
        assert len(mapping.governor_entries) == 2
        assert mapping.governor_entries[0]["is_primary"] is True
        assert mapping.metadata["website"] == "https://compound.finance"

    def test_governor_registry_config_model(self):
        """Test governor registry configuration structure."""
        from models import GovernorRegistryConfig

        config = GovernorRegistryConfig(
            config_version="1.0",
            last_updated="2025-01-15T10:00:00Z",
            networks={
                "mainnet": {
                    "chain_id": 1,
                    "rpc_url": "https://mainnet.infura.io/v3/...",
                    "block_explorer": "https://etherscan.io",
                },
                "goerli": {
                    "chain_id": 5,
                    "rpc_url": "https://goerli.infura.io/v3/...",
                    "block_explorer": "https://goerli.etherscan.io",
                },
            },
            default_network="mainnet",
            cache_ttl=3600,
            hot_reload_enabled=True,
            backup_enabled=True,
        )

        assert config.config_version == "1.0"
        assert config.default_network == "mainnet"
        assert config.networks["mainnet"]["chain_id"] == 1
        assert config.cache_ttl == 3600
        assert config.hot_reload_enabled is True

    def test_network_governor_config_validation(self):
        """Test network-specific governor configuration validation."""
        from models import NetworkGovernorConfig

        network_config = NetworkGovernorConfig(
            network_name="mainnet",
            chain_id=1,
            rpc_url="https://mainnet.infura.io/v3/abc123",
            backup_rpc_urls=[
                "https://eth-mainnet.alchemyapi.io/v2/xyz789",
                "https://mainnet.infura.io/v3/def456",
            ],
            block_explorer_url="https://etherscan.io",
            is_testnet=False,
            gas_estimation_multiplier=1.2,
            max_fee_per_gas="50000000000",  # 50 gwei
            priority_fee_per_gas="2000000000",  # 2 gwei
        )

        assert network_config.network_name == "mainnet"
        assert network_config.chain_id == 1
        assert len(network_config.backup_rpc_urls) == 2
        assert network_config.is_testnet is False
        assert network_config.gas_estimation_multiplier == 1.2


class TestGovernorRegistryCore:
    """Test core governor registry functionality."""

    def test_governor_registry_initialization(self):
        """Test governor registry initialization with default entries."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()
        
        assert registry is not None
        assert hasattr(registry, "entries")
        assert isinstance(registry.entries, dict)
        assert len(registry.entries) >= 4  # Default governors from config

    def test_dynamic_governor_registration(self):
        """Test registering new governor contracts at runtime."""
        from services.governor_registry import GovernorRegistry
        from models import GovernorRegistryEntry

        registry = GovernorRegistry()
        initial_count = len(registry.entries)

        # Register new governor
        new_entry = GovernorRegistryEntry(
            governor_id="uniswap-governance",
            contract_address="0x408ED6354d4973f66138C91495F2f2FCbd8724C3",
            governor_type="UniswapGovernor",
            network="mainnet",
            organization_id="uniswap",
        )

        registry.register_governor(new_entry)

        assert len(registry.entries) == initial_count + 1
        assert "uniswap-governance" in registry.entries
        assert registry.entries["uniswap-governance"].contract_address == "0x408ED6354d4973f66138C91495F2f2FCbd8724C3"

    def test_governor_registration_duplicate_handling(self):
        """Test handling duplicate governor registrations."""
        from services.governor_registry import GovernorRegistry
        from models import GovernorRegistryEntry

        registry = GovernorRegistry()

        entry = GovernorRegistryEntry(
            governor_id="test-governor",
            contract_address="0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234",
            governor_type="TestGovernor",
            network="mainnet",
            organization_id="test-org",
        )

        # First registration should succeed
        registry.register_governor(entry)
        assert "test-governor" in registry.entries

        # Second registration with same ID should raise error or update
        updated_entry = GovernorRegistryEntry(
            governor_id="test-governor",
            contract_address="0x123d35Cc6634C0532925a3b8D1b9667d0e5B4567",
            governor_type="TestGovernorV2",
            network="mainnet",
            organization_id="test-org",
        )

        # Should either raise DuplicateGovernorError or update existing
        registry.register_governor(updated_entry, allow_update=True)
        assert registry.entries["test-governor"].contract_address == "0x123d35Cc6634C0532925a3b8D1b9667d0e5B4567"

    def test_organization_to_governor_mapping(self):
        """Test mapping organization IDs to their governor contracts."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Map compound organization to its governors
        compound_governors = registry.get_governors_by_organization("compound")

        assert compound_governors is not None
        assert len(compound_governors) >= 1
        assert any(g.governor_type == "CompoundBravoGovernor" for g in compound_governors)

    def test_governor_contract_address_validation(self):
        """Test validation and normalization of governor contract addresses."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Test valid address normalization
        valid_address = "0xc0da02939e1441f497fd74f78ce7decb17b66529"  # lowercase
        normalized = registry.normalize_address(valid_address)
        assert normalized == "0xc0Da02939E1441F497fd74F78cE7Decb17B66529"  # checksummed

        # Test invalid address rejection
        with pytest.raises(ValueError):
            registry.normalize_address("invalid-address")

    def test_registry_persistence_and_loading(self):
        """Test saving and loading registry state."""
        from services.governor_registry import GovernorRegistry
        from models import GovernorRegistryEntry

        registry = GovernorRegistry()
        
        # Add custom entry
        custom_entry = GovernorRegistryEntry(
            governor_id="custom-governor",
            contract_address="0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234",
            governor_type="CustomGovernor",
            network="mainnet",
            organization_id="custom-org",
        )
        registry.register_governor(custom_entry)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            registry.save_to_file(temp_file)

            # Load into new registry
            new_registry = GovernorRegistry.load_from_file(temp_file)

            assert "custom-governor" in new_registry.entries
            assert new_registry.entries["custom-governor"].contract_address == "0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234"
        finally:
            os.unlink(temp_file)

    def test_thread_safe_concurrent_access(self):
        """Test thread-safe concurrent access to registry."""
        from services.governor_registry import GovernorRegistry
        from models import GovernorRegistryEntry

        registry = GovernorRegistry()
        results = []
        errors = []

        def register_governor(index):
            try:
                entry = GovernorRegistryEntry(
                    governor_id=f"concurrent-governor-{index}",
                    contract_address=f"0x742d35Cc6634C0532925a3b8D1b9667d0e5B{index:04d}",
                    governor_type="ConcurrentGovernor",
                    network="mainnet",
                    organization_id=f"concurrent-org-{index}",
                )
                registry.register_governor(entry)
                results.append(index)
            except Exception as e:
                errors.append((index, str(e)))

        # Create multiple threads to register governors concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=register_governor, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        assert len(errors) == 0, f"Concurrent access errors: {errors}"
        assert len(results) == 10
        assert all(f"concurrent-governor-{i}" in registry.entries for i in range(10))


class TestConfigurationManagement:
    """Test configuration loading and management."""

    def test_environment_variable_configuration_loading(self):
        """Test loading governor configurations from environment variables."""
        from services.governor_registry import GovernorRegistry

        env_vars = {
            "GOVERNOR_REGISTRY_CUSTOM_DAO": "0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234",
            "GOVERNOR_REGISTRY_ANOTHER_DAO": "0x123d35Cc6634C0532925a3b8D1b9667d0e5B4567",
            "GOVERNOR_REGISTRY_CUSTOM_DAO_TYPE": "CustomGovernor",
            "GOVERNOR_REGISTRY_CUSTOM_DAO_NETWORK": "mainnet",
        }

        with patch.dict(os.environ, env_vars):
            registry = GovernorRegistry.from_environment()

            assert "custom-dao" in registry.entries
            assert registry.entries["custom-dao"].contract_address == "0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234"
            assert "another-dao" in registry.entries

    def test_json_configuration_file_loading(self):
        """Test loading governor configurations from JSON files."""
        from services.governor_registry import GovernorRegistry

        config_data = {
            "version": "1.0",
            "governors": {
                "test-dao": {
                    "contract_address": "0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234",
                    "governor_type": "TestGovernor",
                    "network": "mainnet",
                    "organization_id": "test-org",
                }
            },
            "networks": {
                "mainnet": {
                    "chain_id": 1,
                    "rpc_url": "https://mainnet.infura.io/v3/test"
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            registry = GovernorRegistry.from_config_file(temp_file)

            assert "test-dao" in registry.entries
            assert registry.entries["test-dao"].contract_address == "0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234"
        finally:
            os.unlink(temp_file)

    def test_configuration_hierarchy_precedence(self):
        """Test configuration hierarchy: env vars > config files > defaults."""
        from services.governor_registry import GovernorRegistry

        # Create config file
        config_data = {
            "governors": {
                "test-dao": {
                    "contract_address": "0x111d35Cc6634C0532925a3b8D1b9667d0e5B1111",
                    "governor_type": "FileGovernor",
                    "network": "mainnet",
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            # Environment variable should override config file
            env_vars = {
                "GOVERNOR_REGISTRY_TEST_DAO": "0x222d35Cc6634C0532925a3b8D1b9667d0e5B2222"
            }

            with patch.dict(os.environ, env_vars):
                registry = GovernorRegistry.from_config_file(temp_file)
                registry.load_from_environment()

                # Environment variable should take precedence
                assert registry.entries["test-dao"].contract_address == "0x222d35Cc6634C0532925a3b8D1b9667d0e5B2222"
        finally:
            os.unlink(temp_file)

    def test_configuration_hot_reloading(self):
        """Test hot reloading of configurations without service restart."""
        from services.governor_registry import GovernorRegistry

        config_data = {
            "governors": {
                "hot-reload-dao": {
                    "contract_address": "0x111d35Cc6634C0532925a3b8D1b9667d0e5B1111",
                    "governor_type": "OriginalGovernor",
                    "network": "mainnet",
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            temp_file = f.name

        try:
            registry = GovernorRegistry.from_config_file(temp_file)
            assert registry.entries["hot-reload-dao"].governor_type == "OriginalGovernor"

            # Update config file
            updated_config = {
                "governors": {
                    "hot-reload-dao": {
                        "contract_address": "0x222d35Cc6634C0532925a3b8D1b9667d0e5B2222",
                        "governor_type": "UpdatedGovernor",
                        "network": "mainnet",
                    }
                }
            }

            with open(temp_file, 'w') as f:
                json.dump(updated_config, f)

            # Hot reload
            registry.reload_configuration(temp_file)

            assert registry.entries["hot-reload-dao"].contract_address == "0x222d35Cc6634C0532925a3b8D1b9667d0e5B2222"
            assert registry.entries["hot-reload-dao"].governor_type == "UpdatedGovernor"
        finally:
            os.unlink(temp_file)

    def test_configuration_validation_with_detailed_errors(self):
        """Test configuration validation with detailed error reporting."""
        from services.governor_registry import GovernorRegistry, ConfigurationValidationError

        invalid_config = {
            "governors": {
                "invalid-dao": {
                    "contract_address": "invalid-address",  # Invalid address
                    "governor_type": "",  # Empty type
                    "network": "unknown-network",  # Unknown network
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_config, f)
            temp_file = f.name

        try:
            with pytest.raises(ConfigurationValidationError) as exc_info:
                GovernorRegistry.from_config_file(temp_file)

            error = exc_info.value
            assert "invalid-address" in str(error)
            assert "governor_type" in str(error)
            assert "unknown-network" in str(error)
        finally:
            os.unlink(temp_file)


class TestMultiNetworkSupport:
    """Test multi-network configuration and support."""

    def test_network_specific_governor_configurations(self):
        """Test network-specific governor configurations."""
        from services.governor_registry import GovernorRegistry
        from models import GovernorRegistryEntry

        registry = GovernorRegistry()

        # Register governors for different networks
        mainnet_entry = GovernorRegistryEntry(
            governor_id="multi-network-dao-mainnet",
            contract_address="0x111d35Cc6634C0532925a3b8D1b9667d0e5B1111",
            governor_type="MainnetGovernor",
            network="mainnet",
            organization_id="multi-network-dao",
        )

        goerli_entry = GovernorRegistryEntry(
            governor_id="multi-network-dao-goerli",
            contract_address="0x222d35Cc6634C0532925a3b8D1b9667d0e5B2222",
            governor_type="TestnetGovernor",
            network="goerli",
            organization_id="multi-network-dao",
        )

        registry.register_governor(mainnet_entry)
        registry.register_governor(goerli_entry)

        # Get governors by network
        mainnet_governors = registry.get_governors_by_network("mainnet")
        goerli_governors = registry.get_governors_by_network("goerli")

        assert any(g.governor_id == "multi-network-dao-mainnet" for g in mainnet_governors)
        assert any(g.governor_id == "multi-network-dao-goerli" for g in goerli_governors)

    def test_automatic_network_detection_and_selection(self):
        """Test automatic network detection and governor selection."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Mock network detection
        with patch('services.governor_registry.detect_current_network') as mock_detect:
            mock_detect.return_value = "mainnet"

            # Get governor for organization with auto-detection
            governor = registry.get_governor_for_organization("compound", auto_detect_network=True)

            assert governor is not None
            assert governor.network == "mainnet"
            mock_detect.assert_called_once()

    def test_fallback_to_mainnet_configuration(self):
        """Test fallback to mainnet configuration when testnet not available."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Request governor for organization on testnet that doesn't exist
        governor = registry.get_governor_for_organization(
            "compound", 
            network="goerli", 
            fallback_to_mainnet=True
        )

        # Should fallback to mainnet
        assert governor is not None
        assert governor.network == "mainnet"

    def test_rpc_endpoint_management_per_network(self):
        """Test RPC endpoint management for different networks."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Configure network endpoints
        network_config = {
            "mainnet": {
                "primary_rpc": "https://mainnet.infura.io/v3/primary",
                "backup_rpcs": [
                    "https://mainnet.infura.io/v3/backup1",
                    "https://eth-mainnet.alchemyapi.io/v2/backup2"
                ]
            },
            "goerli": {
                "primary_rpc": "https://goerli.infura.io/v3/primary",
                "backup_rpcs": ["https://goerli.infura.io/v3/backup1"]
            }
        }

        registry.configure_networks(network_config)

        # Get RPC endpoints
        mainnet_rpc = registry.get_primary_rpc("mainnet")
        mainnet_backups = registry.get_backup_rpcs("mainnet")
        goerli_rpc = registry.get_primary_rpc("goerli")

        assert mainnet_rpc == "https://mainnet.infura.io/v3/primary"
        assert len(mainnet_backups) == 2
        assert goerli_rpc == "https://goerli.infura.io/v3/primary"

    def test_network_switching_and_configuration_updates(self):
        """Test network switching and configuration updates."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Initial network
        assert registry.current_network == "mainnet"  # default

        # Switch network
        registry.switch_network("goerli")
        assert registry.current_network == "goerli"

        # Update network configuration
        new_config = {
            "goerli": {
                "chain_id": 5,
                "rpc_url": "https://new-goerli-endpoint.com"
            }
        }

        registry.update_network_configuration(new_config)
        goerli_config = registry.get_network_config("goerli")

        assert goerli_config["rpc_url"] == "https://new-goerli-endpoint.com"


class TestOrganizationRegistry:
    """Test organization registry functionality."""

    def test_organization_to_governor_mapping(self):
        """Test mapping organization names/IDs to governor contracts."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Map organization to governor
        mapping = registry.get_organization_mapping("compound")

        assert mapping is not None
        assert mapping.organization_id == "compound"
        assert len(mapping.governor_entries) >= 1
        assert any(entry["governor_type"] == "CompoundBravoGovernor" for entry in mapping.governor_entries)

    def test_organization_metadata_and_governance_info(self):
        """Test organization metadata and governance information."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Get organization info
        org_info = registry.get_organization_info("compound")

        assert org_info is not None
        assert org_info.organization_id == "compound"
        assert org_info.name == "Compound"
        assert "governance_forum" in org_info.metadata
        assert "website" in org_info.metadata

    def test_dynamic_organization_registration_and_updates(self):
        """Test dynamic organization registration and updates."""
        from services.governor_registry import GovernorRegistry
        from models import OrganizationGovernorMapping

        registry = GovernorRegistry()

        # Register new organization
        new_org = OrganizationGovernorMapping(
            organization_id="new-dao",
            organization_name="New DAO",
            governor_entries=[
                {
                    "governor_id": "new-dao-governor",
                    "contract_address": "0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234",
                    "governor_type": "NewDAOGovernor",
                    "network": "mainnet",
                    "is_primary": True,
                }
            ],
            metadata={"description": "A new decentralized organization"},
        )

        registry.register_organization(new_org)

        # Verify registration
        retrieved_org = registry.get_organization_mapping("new-dao")
        assert retrieved_org.organization_name == "New DAO"
        assert len(retrieved_org.governor_entries) == 1

    def test_organization_specific_configuration_overrides(self):
        """Test organization-specific configuration overrides."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Set organization-specific overrides
        overrides = {
            "compound": {
                "gas_multiplier": 1.5,
                "priority_fee": "3000000000",  # 3 gwei
                "custom_settings": {"fast_finality": True}
            }
        }

        registry.set_organization_overrides(overrides)

        # Get organization config with overrides
        compound_config = registry.get_organization_config("compound")

        assert compound_config["gas_multiplier"] == 1.5
        assert compound_config["priority_fee"] == "3000000000"
        assert compound_config["custom_settings"]["fast_finality"] is True

    def test_batch_organization_lookups_and_caching(self):
        """Test batch organization lookups and caching."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Batch lookup organizations
        org_ids = ["compound", "uniswap", "aave"]
        batch_results = registry.batch_get_organizations(org_ids)

        assert len(batch_results) == len(org_ids)
        assert all(org_id in batch_results for org_id in org_ids)
        assert all(result is not None for result in batch_results.values())

        # Second call should use cache
        with patch.object(registry, '_fetch_organization_info') as mock_fetch:
            batch_results_cached = registry.batch_get_organizations(org_ids)
            mock_fetch.assert_not_called()  # Should use cache


class TestAdvancedRegistryFeatures:
    """Test advanced registry features."""

    def test_governor_contract_versioning_and_upgrades(self):
        """Test governor contract versioning and upgrade handling."""
        from services.governor_registry import GovernorRegistry
        from models import GovernorRegistryEntry

        registry = GovernorRegistry()

        # Register v1 governor
        governor_v1 = GovernorRegistryEntry(
            governor_id="versioned-dao-v1",
            contract_address="0x111d35Cc6634C0532925a3b8D1b9667d0e5B1111",
            governor_type="VersionedGovernorV1",
            network="mainnet",
            organization_id="versioned-dao",
            abi_version="1.0",
            deployment_block=12000000,
        )

        registry.register_governor(governor_v1)

        # Register v2 governor (upgrade)
        governor_v2 = GovernorRegistryEntry(
            governor_id="versioned-dao-v2",
            contract_address="0x222d35Cc6634C0532925a3b8D1b9667d0e5B2222",
            governor_type="VersionedGovernorV2",
            network="mainnet",
            organization_id="versioned-dao",
            abi_version="2.0",
            deployment_block=15000000,
            replaces_governor_id="versioned-dao-v1",
        )

        registry.register_governor(governor_v2)

        # Get current governor (should be v2)
        current_governor = registry.get_current_governor("versioned-dao")
        assert current_governor.governor_id == "versioned-dao-v2"

        # Get governor for specific block (should be v1)
        historical_governor = registry.get_governor_at_block("versioned-dao", 13000000)
        assert historical_governor.governor_id == "versioned-dao-v1"

    def test_deprecated_contract_handling_and_migration(self):
        """Test deprecated contract handling and migration paths."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Mark governor as deprecated
        registry.deprecate_governor("compound-alpha", reason="Replaced by Bravo", migration_path="compound-bravo")

        # Get deprecated governors
        deprecated = registry.get_deprecated_governors()
        assert "compound-alpha" in [g.governor_id for g in deprecated]

        # Get migration path
        migration = registry.get_migration_path("compound-alpha")
        assert migration == "compound-bravo"

    def test_registry_export_import_for_backup_and_migration(self):
        """Test registry export/import for backup and migration."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Export registry
        export_data = registry.export_registry()

        assert "version" in export_data
        assert "governors" in export_data
        assert "organizations" in export_data
        assert "networks" in export_data

        # Import into new registry
        new_registry = GovernorRegistry()
        new_registry.import_registry(export_data)

        # Verify import
        assert len(new_registry.entries) == len(registry.entries)
        for governor_id in registry.entries:
            assert governor_id in new_registry.entries

    def test_registry_validation_and_integrity_checks(self):
        """Test registry validation and integrity checks."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Run validation
        validation_results = registry.validate_registry()

        assert validation_results["is_valid"] is True
        assert "address_validation" in validation_results
        assert "network_validation" in validation_results
        assert "organization_mapping_validation" in validation_results

        # Add invalid entry and revalidate
        from models import GovernorRegistryEntry
        invalid_entry = GovernorRegistryEntry(
            governor_id="invalid-governor",
            contract_address="invalid-address",
            governor_type="InvalidGovernor",
            network="unknown-network",
            organization_id="unknown-org",
        )

        # Validation should catch this
        with pytest.raises(ValidationError):
            registry.register_governor(invalid_entry)

    def test_registry_performance_with_large_datasets(self):
        """Test registry performance with large numbers of organizations."""
        from services.governor_registry import GovernorRegistry
        from models import GovernorRegistryEntry

        registry = GovernorRegistry()

        # Register large number of governors
        start_time = time.time()
        for i in range(1000):
            entry = GovernorRegistryEntry(
                governor_id=f"perf-test-governor-{i}",
                contract_address=f"0x742d35Cc6634C0532925a3b8D1b9667d0e5B{i:04d}",
                governor_type="PerfTestGovernor",
                network="mainnet",
                organization_id=f"perf-test-org-{i}",
            )
            registry.register_governor(entry)

        registration_time = time.time() - start_time

        # Test lookup performance
        start_time = time.time()
        for i in range(100):
            governor = registry.get_governor(f"perf-test-governor-{i}")
            assert governor is not None

        lookup_time = time.time() - start_time

        # Performance assertions
        assert registration_time < 10.0  # Should register 1000 governors in < 10 seconds
        assert lookup_time < 1.0  # Should lookup 100 governors in < 1 second


class TestConfigurationSources:
    """Test configuration sources and loading."""

    def test_loading_from_remote_urls_with_caching(self):
        """Test loading configurations from remote URLs with caching."""
        from services.governor_registry import GovernorRegistry

        mock_response = {
            "governors": {
                "remote-dao": {
                    "contract_address": "0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234",
                    "governor_type": "RemoteGovernor",
                    "network": "mainnet",
                }
            }
        }

        with patch('httpx.get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.status_code = 200

            registry = GovernorRegistry.from_remote_url("https://config.example.com/governors.json")

            assert "remote-dao" in registry.entries
            mock_get.assert_called_once()

            # Second call should use cache
            registry2 = GovernorRegistry.from_remote_url("https://config.example.com/governors.json")
            assert mock_get.call_count == 1  # Should use cached result

    def test_configuration_merging_and_priority_resolution(self):
        """Test configuration merging and priority resolution."""
        from services.governor_registry import GovernorRegistry

        # Create multiple config sources
        base_config = {
            "governors": {
                "test-dao": {
                    "contract_address": "0x111d35Cc6634C0532925a3b8D1b9667d0e5B1111",
                    "governor_type": "BaseGovernor",
                    "network": "mainnet",
                }
            }
        }

        override_config = {
            "governors": {
                "test-dao": {
                    "contract_address": "0x222d35Cc6634C0532925a3b8D1b9667d0e5B2222",
                    "governor_type": "OverrideGovernor",
                    # network should inherit from base
                }
            }
        }

        registry = GovernorRegistry()
        registry.merge_configurations([base_config, override_config])

        # Override should take precedence, but missing fields should inherit
        entry = registry.entries["test-dao"]
        assert entry.contract_address == "0x222d35Cc6634C0532925a3b8D1b9667d0e5B2222"
        assert entry.governor_type == "OverrideGovernor"
        assert entry.network == "mainnet"  # Inherited from base

    def test_configuration_schema_validation(self):
        """Test configuration schema validation."""
        from services.governor_registry import GovernorRegistry, ConfigurationSchemaError

        invalid_config = {
            "governors": {
                "missing-required-fields": {
                    "contract_address": "0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234",
                    # Missing governor_type and network
                }
            }
        }

        with pytest.raises(ConfigurationSchemaError) as exc_info:
            registry = GovernorRegistry()
            registry.load_configuration(invalid_config)

        assert "governor_type" in str(exc_info.value)
        assert "network" in str(exc_info.value)


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""

    def test_unknown_organization_handling_with_fallback(self):
        """Test unknown organization handling with fallback mechanisms."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Request unknown organization
        unknown_gov = registry.get_governor_for_organization("unknown-dao")
        assert unknown_gov is None

        # With fallback enabled
        fallback_gov = registry.get_governor_for_organization(
            "unknown-dao", 
            fallback_to_default=True
        )
        assert fallback_gov is not None
        assert fallback_gov.organization_id == "default"

    def test_malformed_configuration_data_recovery(self):
        """Test recovery from malformed configuration data."""
        from services.governor_registry import GovernorRegistry

        malformed_config = '{"governors": {"test": invalid json}'

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write(malformed_config)
            temp_file = f.name

        try:
            # Should not crash, should use defaults or skip malformed parts
            registry = GovernorRegistry.from_config_file(temp_file, strict=False)
            assert registry is not None
            # Should still have default governors
            assert len(registry.entries) > 0
        finally:
            os.unlink(temp_file)

    def test_network_connectivity_issues_during_remote_loading(self):
        """Test handling network connectivity issues during remote config loading."""
        from services.governor_registry import GovernorRegistry
        import httpx

        with patch('httpx.get') as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection failed")

            # Should fallback gracefully
            registry = GovernorRegistry.from_remote_url(
                "https://unreachable.example.com/config.json",
                fallback_to_defaults=True
            )

            assert registry is not None
            assert len(registry.entries) > 0  # Should have defaults

    def test_concurrent_modification_detection_and_resolution(self):
        """Test concurrent modification detection and resolution."""
        from services.governor_registry import GovernorRegistry, ConcurrentModificationError

        registry = GovernorRegistry()

        # Simulate concurrent modification
        def modify_registry():
            time.sleep(0.1)
            registry._version += 1  # Simulate external modification

        # Start modification in background
        thread = threading.Thread(target=modify_registry)
        thread.start()

        # Try to modify registry - should detect concurrent modification
        with pytest.raises(ConcurrentModificationError):
            registry.bulk_update_governors([], check_version=True)

        thread.join()

    def test_configuration_rollback_on_validation_failures(self):
        """Test configuration rollback on validation failures."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()
        original_count = len(registry.entries)

        # Try to load invalid configuration
        invalid_config = {
            "governors": {
                "valid-dao": {
                    "contract_address": "0x742d35Cc6634C0532925a3b8D1b9667d0e5B1234",
                    "governor_type": "ValidGovernor",
                    "network": "mainnet",
                },
                "invalid-dao": {
                    "contract_address": "invalid-address",
                    "governor_type": "InvalidGovernor",
                    "network": "mainnet",
                }
            }
        }

        # Should rollback to original state on validation failure
        with pytest.raises(ValidationError):
            registry.load_configuration(invalid_config, atomic=True)

        # Registry should be unchanged
        assert len(registry.entries) == original_count


class TestPerformanceAndCaching:
    """Test performance and caching features."""

    def test_registry_lookup_performance_with_large_datasets(self):
        """Test registry lookup performance with large datasets."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Add large number of entries
        for i in range(10000):
            from models import GovernorRegistryEntry
            entry = GovernorRegistryEntry(
                governor_id=f"large-test-{i}",
                contract_address=f"0x742d35Cc6634C0532925a3b8D1b9667d0e5B{i:04x}",
                governor_type="LargeTestGovernor",
                network="mainnet",
                organization_id=f"large-org-{i}",
            )
            registry.register_governor(entry)

        # Test lookup performance
        start_time = time.time()
        for i in range(1000):
            result = registry.get_governor(f"large-test-{i}")
            assert result is not None

        lookup_time = time.time() - start_time
        assert lookup_time < 1.0  # Should be fast even with large dataset

    def test_configuration_caching_and_ttl_management(self):
        """Test configuration caching and TTL management."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Set short TTL for testing
        registry.set_cache_ttl(1)  # 1 second

        # Cache some data
        config_data = {"test": "data"}
        registry.cache_configuration("test-key", config_data)

        # Should be cached
        cached_data = registry.get_cached_configuration("test-key")
        assert cached_data == config_data

        # Wait for TTL expiration
        time.sleep(2)

        # Should be expired
        expired_data = registry.get_cached_configuration("test-key")
        assert expired_data is None

    def test_registry_search_and_filtering_capabilities(self):
        """Test registry search and filtering capabilities."""
        from services.governor_registry import GovernorRegistry

        registry = GovernorRegistry()

        # Search by governor type
        compound_governors = registry.search_governors(governor_type="CompoundBravoGovernor")
        assert len(compound_governors) >= 1
        assert all(g.governor_type == "CompoundBravoGovernor" for g in compound_governors)

        # Search by network
        mainnet_governors = registry.search_governors(network="mainnet")
        assert len(mainnet_governors) >= 1
        assert all(g.network == "mainnet" for g in mainnet_governors)

        # Complex search with multiple filters
        filtered_governors = registry.search_governors(
            governor_type="CompoundBravoGovernor",
            network="mainnet",
            organization_id="compound"
        )
        assert len(filtered_governors) >= 1

    def test_memory_usage_optimization_for_large_registries(self):
        """Test memory usage optimization for large registries."""
        from services.governor_registry import GovernorRegistry
        import psutil
        import gc

        # Measure initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss

        registry = GovernorRegistry()

        # Add many entries
        for i in range(5000):
            from models import GovernorRegistryEntry
            entry = GovernorRegistryEntry(
                governor_id=f"memory-test-{i}",
                contract_address=f"0x742d35Cc6634C0532925a3b8D1b9667d0e5B{i:04x}",
                governor_type="MemoryTestGovernor",
                network="mainnet",
                organization_id=f"memory-org-{i}",
            )
            registry.register_governor(entry)

        # Force garbage collection
        gc.collect()

        # Measure memory after additions
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 100MB for 5000 entries)
        assert memory_increase < 100 * 1024 * 1024  # 100MB


# Exception classes that should exist
class TestGovernorRegistryExceptions:
    """Test registry-specific exception classes."""

    def test_duplicate_governor_error(self):
        """Test DuplicateGovernorError exception."""
        from services.governor_registry import DuplicateGovernorError

        error = DuplicateGovernorError("compound-bravo", "Governor already exists")
        assert error.governor_id == "compound-bravo"
        assert "already exists" in str(error)

    def test_configuration_validation_error(self):
        """Test ConfigurationValidationError exception."""
        from services.governor_registry import ConfigurationValidationError

        error = ConfigurationValidationError("Invalid address format", field="contract_address")
        assert error.field == "contract_address"
        assert "Invalid address" in str(error)

    def test_network_not_found_error(self):
        """Test NetworkNotFoundError exception."""
        from services.governor_registry import NetworkNotFoundError

        error = NetworkNotFoundError("unknown-network")
        assert error.network_name == "unknown-network"

    def test_concurrent_modification_error(self):
        """Test ConcurrentModificationError exception."""
        from services.governor_registry import ConcurrentModificationError

        error = ConcurrentModificationError("Registry modified during operation")
        assert "modified during operation" in str(error)