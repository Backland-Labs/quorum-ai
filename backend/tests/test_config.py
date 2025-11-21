"""Test configuration settings for Olas Agent Architecture."""

import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError

from config import Settings


class TestBlockchainConfiguration:
    """Test blockchain configuration settings."""

    def test_chain_name_defaults_to_celo(self):
        """Test that chain_name defaults to 'celo'."""
        settings = Settings()
        assert settings.chain_name == "celo"

    def test_celo_rpc_defaults_to_empty_string(self):
        """Test that celo_rpc defaults to empty string."""
        settings = Settings()
        assert settings.celo_rpc == ""

    def test_celo_rpc_loaded_from_env(self):
        """Test that celo_rpc is loaded from CELO_LEDGER_RPC environment variable."""
        test_rpc = "https://forno.celo.org"
        with patch.dict(os.environ, {"CELO_LEDGER_RPC": test_rpc}):
            settings = Settings()
            assert settings.celo_rpc == test_rpc

    def test_safe_addresses_loaded_from_env_comma_separated(self):
        """Test that safe_addresses is loaded from SAFE_CONTRACT_ADDRESSES environment variable (comma-separated format)."""
        test_addresses = "dao1:0x123,dao2:0x456"
        with patch.dict(os.environ, {"SAFE_CONTRACT_ADDRESSES": test_addresses}):
            settings = Settings()
            expected = {"dao1": "0x123", "dao2": "0x456"}
            assert settings.safe_addresses == expected

    def test_safe_addresses_loaded_from_env_json_format(self):
        """Test that safe_contract_addresses is loaded from prefixed env var with JSON format."""
        test_addresses = '{"base":"0x55196464De636b8ddA93Bdf78831b3aA0e429d60"}'
        with patch.dict(os.environ, {"CONNECTION_CONFIGS_CONFIG_SAFE_CONTRACT_ADDRESSES": test_addresses}, clear=False):
            settings = Settings(_env_file=None)
            expected = {"base": "0x55196464De636b8ddA93Bdf78831b3aA0e429d60"}
            assert settings.safe_contract_addresses == expected

    def test_base_safe_address_auto_assigned_from_json_base_key(self):
        """Test that base_safe_address is auto-assigned when 'base' key exists in JSON format."""
        test_addresses = (
            '{"base": "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca", "gnosis": "0x456"}'
        )
        with patch.dict(os.environ, {"SAFE_CONTRACT_ADDRESSES": test_addresses, "BASE_SAFE_ADDRESS": ""}, clear=False):
            settings = Settings()
            assert (
                settings.base_safe_address
                == "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca"
            )
            assert (
                settings.safe_addresses["base"]
                == "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca"
            )

    def test_base_safe_address_auto_assigned_from_comma_separated_base_key(self):
        """Test that base_safe_address is auto-assigned when 'base' key exists in comma-separated format."""
        test_addresses = "base:0x07edA994E013AbC8619A5038455db3A6FBdd2Bca,gnosis:0x456"
        with patch.dict(os.environ, {"SAFE_CONTRACT_ADDRESSES": test_addresses, "BASE_SAFE_ADDRESS": ""}, clear=False):
            settings = Settings()
            assert (
                settings.base_safe_address
                == "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca"
            )
            assert (
                settings.safe_addresses["base"]
                == "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca"
            )

    def test_base_safe_address_not_overridden_if_already_set(self):
        """Test that base_safe_address is not overridden if it's already explicitly set."""
        test_addresses = '{"base": "0x07edA994E013AbC8619A5038455db3A6FBdd2Bca"}'
        with patch.dict(
            os.environ,
            {"SAFE_CONTRACT_ADDRESSES": test_addresses, "BASE_SAFE_ADDRESS": "0x999"},
        ):
            settings = Settings()
            # The explicitly set BASE_SAFE_ADDRESS should take precedence
            assert settings.base_safe_address == "0x999"

    def test_agent_address_defaults_to_none(self):
        """Test that agent_address defaults to None."""
        settings = Settings()
        assert settings.agent_address is None

    def test_agent_address_loaded_from_env(self):
        """Test that agent_address is loaded from AGENT_ADDRESS environment variable."""
        test_address = "0x789abcdef"
        with patch.dict(os.environ, {"AGENT_ADDRESS": test_address}):
            settings = Settings()
            assert settings.agent_address == test_address

    def test_chain_name_validation(self):
        """Test that chain_name accepts valid blockchain names."""
        valid_chains = ["celo", "ethereum", "polygon", "arbitrum"]
        for chain in valid_chains:
            with patch.dict(os.environ, {"CHAIN_NAME": chain}):
                settings = Settings()
                assert settings.chain_name == chain

    def test_safe_addresses_parsing_edge_cases(self):
        """Test safe_addresses parsing with edge cases."""
        # Test with spaces
        with patch.dict(
            os.environ, {"SAFE_CONTRACT_ADDRESSES": "dao1: 0x123 , dao2: 0x456 "}
        ):
            settings = Settings()
            expected = {"dao1": "0x123", "dao2": "0x456"}
            assert settings.safe_addresses == expected

        # Test with empty values
        with patch.dict(
            os.environ, {"SAFE_CONTRACT_ADDRESSES": "dao1:0x123,,dao2:0x456"}
        ):
            settings = Settings()
            expected = {"dao1": "0x123", "dao2": "0x456"}
            assert settings.safe_addresses == expected

        # Test with malformed entries
        with patch.dict(
            os.environ, {"SAFE_CONTRACT_ADDRESSES": "dao1:0x123,invalid,dao2:0x456"}
        ):
            settings = Settings()
            expected = {"dao1": "0x123", "dao2": "0x456"}
            assert settings.safe_addresses == expected


class TestAgentSpecificSettings:
    """Test agent-specific configuration settings."""

    def test_activity_check_interval_defaults_to_3600(self):
        """Test that activity_check_interval defaults to 3600 seconds (1 hour)."""
        settings = Settings()
        assert settings.activity_check_interval == 3600

    def test_activity_check_interval_loaded_from_env(self):
        """Test that activity_check_interval is loaded from environment variable."""
        test_interval = 7200  # 2 hours
        with patch.dict(os.environ, {"ACTIVITY_CHECK_INTERVAL": str(test_interval)}):
            settings = Settings()
            assert settings.activity_check_interval == test_interval

    def test_proposal_check_interval_defaults_to_300(self):
        """Test that proposal_check_interval defaults to 300 seconds (5 minutes)."""
        settings = Settings()
        assert settings.proposal_check_interval == 300

    def test_proposal_check_interval_loaded_from_env(self):
        """Test that proposal_check_interval is loaded from environment variable."""
        test_interval = 600  # 10 minutes
        with patch.dict(os.environ, {"PROPOSAL_CHECK_INTERVAL": str(test_interval)}):
            settings = Settings()
            assert settings.proposal_check_interval == test_interval

    def test_min_time_before_deadline_defaults_to_1800(self):
        """Test that min_time_before_deadline defaults to 1800 seconds (30 minutes)."""
        settings = Settings()
        assert settings.min_time_before_deadline == 1800

    def test_min_time_before_deadline_loaded_from_env(self):
        """Test that min_time_before_deadline is loaded from environment variable."""
        test_time = 3600  # 1 hour
        with patch.dict(os.environ, {"MIN_TIME_BEFORE_DEADLINE": str(test_time)}):
            settings = Settings()
            assert settings.min_time_before_deadline == test_time

    def test_intervals_validation(self):
        """Test that interval values are positive integers."""
        # Test valid values
        valid_intervals = [1, 60, 300, 3600, 86400]
        for interval in valid_intervals:
            with patch.dict(os.environ, {"ACTIVITY_CHECK_INTERVAL": str(interval)}):
                settings = Settings()
                assert settings.activity_check_interval == interval

        # Test invalid values should raise validation error
        invalid_intervals = [-1, 0]
        for interval in invalid_intervals:
            with patch.dict(os.environ, {"ACTIVITY_CHECK_INTERVAL": str(interval)}):
                with pytest.raises(ValueError):
                    Settings()


class TestOlasStakingConfiguration:
    """Test Olas staking configuration settings."""

    def test_staking_contract_address_has_default(self):
        """Test that staking_contract_address has a default value."""
        settings = Settings()
        assert settings.staking_contract_address == "0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb"

    def test_staking_contract_address_loaded_from_env(self):
        """Test that staking_contract_address is loaded from environment variable."""
        test_address = "0x123456789abcdef"
        with patch.dict(os.environ, {"STAKING_CONTRACT_ADDRESS": test_address}):
            settings = Settings()
            assert settings.staking_contract_address == test_address

    def test_activity_checker_contract_address_has_default(self):
        """Test that activity_checker_contract_address has a default value."""
        settings = Settings()
        assert settings.activity_checker_contract_address == "0x747262cC12524C571e08faCb6E6994EF2E3B97ab"

    def test_activity_checker_contract_address_loaded_from_env(self):
        """Test that activity_checker_contract_address is loaded from environment variable."""
        test_address = "0x987654321fedcba"
        with patch.dict(
            os.environ, {"ACTIVITY_CHECKER_CONTRACT_ADDRESS": test_address}
        ):
            settings = Settings()
            assert settings.activity_checker_contract_address == test_address

    def test_service_registry_token_utility_contract_defaults_to_none(self):
        """Test that service_registry_token_utility_contract defaults to None."""
        settings = Settings()
        assert settings.service_registry_token_utility_contract is None

    def test_service_registry_token_utility_contract_loaded_from_env(self):
        """Test that service_registry_token_utility_contract is loaded from environment variable."""
        test_address = "0xabcdef123456789"
        with patch.dict(
            os.environ, {"SERVICE_REGISTRY_TOKEN_UTILITY_CONTRACT": test_address}
        ):
            settings = Settings()
            assert settings.service_registry_token_utility_contract == test_address

    def test_all_staking_contracts_loaded_together(self):
        """Test that all staking contract addresses can be loaded together."""
        test_staking = "0x111111111111111"
        test_activity = "0x222222222222222"

        env_vars = {
            "STAKING_CONTRACT_ADDRESS": test_staking,
            "ACTIVITY_CHECKER_CONTRACT_ADDRESS": test_activity,
        }

        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.staking_contract_address == test_staking
            assert settings.activity_checker_contract_address == test_activity
            assert settings.service_registry_token_utility_contract == test_registry

    def test_staking_contract_addresses_validation(self):
        """Test that contract addresses can be overridden with environment variables."""
        test_address = "0x999999999999999"
        with patch.dict(os.environ, {"STAKING_CONTRACT_ADDRESS": test_address}):
            settings = Settings()
            assert settings.staking_contract_address == test_address

    def test_staking_contract_addresses_are_optional(self):
        """Test that all staking contract addresses are optional."""
        settings = Settings()

        # staking_contract_address has a default, others are None
        assert settings.staking_contract_address == "0xeF662b5266db0AeFe55554c50cA6Ad25c1DA16fb"
        assert settings.activity_checker_contract_address == "0x747262cC12524C571e08faCb6E6994EF2E3B97ab"
        assert settings.service_registry_token_utility_contract is None

        # Should be able to create settings without any staking config
        assert isinstance(settings, Settings)


class TestAttestationTrackerConfiguration:
    """Test AttestationTracker configuration settings."""

    def test_attestation_tracker_address_loaded_from_env(self):
        """Test that attestation_tracker_address is loaded from environment variable."""
        test_address = "0x1234567890abcdef1234567890abcdef12345678"
        expected_checksum = "0x1234567890AbcdEF1234567890aBcdef12345678"
        with patch.dict(os.environ, {"ATTESTATION_TRACKER_ADDRESS": test_address}):
            settings = Settings()
            assert settings.attestation_tracker_address == expected_checksum

    def test_attestation_tracker_address_validation_valid_address(self):
        """Test that valid Ethereum addresses are accepted and converted to checksum format."""
        test_cases = [
            (
                "0x1234567890abcdef1234567890abcdef12345678",
                "0x1234567890AbcdEF1234567890aBcdef12345678",
            ),
            (
                "0xAbCdEf123456789ABCDef123456789abcdef1234",
                "0xABCDEF123456789abcdeF123456789ABCDEf1234",
            ),
        ]
        for input_address, expected_address in test_cases:
            with patch.dict(os.environ, {"ATTESTATION_TRACKER_ADDRESS": input_address}):
                settings = Settings()
                assert settings.attestation_tracker_address == expected_address

    def test_attestation_tracker_address_validation_invalid_address(self):
        """Test that invalid Ethereum addresses are rejected."""
        invalid_addresses = [
            "0x123",  # Too short
            "invalid_address",  # Not hex
            "1234567890abcdef1234567890abcdef1234567",  # Too short (39 chars)
        ]
        for address in invalid_addresses:
            with patch.dict(os.environ, {"ATTESTATION_TRACKER_ADDRESS": address}):
                # Invalid addresses should raise validation error (Pydantic ValidationError)
                with pytest.raises((ValueError, ValidationError)):
                    Settings()

    def test_attestation_tracker_address_empty_string_allowed(self):
        """Test that empty string is treated as None."""
        with patch.dict(os.environ, {"ATTESTATION_TRACKER_ADDRESS": ""}):
            settings = Settings()
            # Empty string should result in None
            assert settings.attestation_tracker_address in [None, ""]

    def test_attestation_tracker_address_checksum_conversion(self):
        """Test that valid addresses are converted to checksum format."""
        # Test address without checksum (all lowercase)
        test_address = "1234567890abcdef1234567890abcdef12345678"
        expected_checksum = "0x1234567890AbcdEF1234567890aBcdef12345678"
        with patch.dict(os.environ, {"ATTESTATION_TRACKER_ADDRESS": test_address}):
            settings = Settings()
            assert settings.attestation_tracker_address == expected_checksum

    def test_attestation_chain_defaults_to_base(self):
        """Test that attestation_chain defaults to 'base'."""
        settings = Settings()
        assert settings.attestation_chain == "base"

    def test_attestation_chain_loaded_from_env(self):
        """Test that attestation_chain is loaded from environment variable."""
        test_chain = "ethereum"
        with patch.dict(os.environ, {"ATTESTATION_CHAIN": test_chain}):
            settings = Settings()
            assert settings.attestation_chain == test_chain


class TestPrefixedEnvironmentVariables:
    """Test environment variable loading with CONNECTION_CONFIGS_CONFIG_ prefix."""

    def test_openrouter_api_key_loaded_from_prefixed_env(self):
        """Test that openrouter_api_key is loaded from CONNECTION_CONFIGS_CONFIG_OPENROUTER_API_KEY."""
        test_api_key = "sk-or-v1-test123456789"
        with patch.dict(os.environ, {"CONNECTION_CONFIGS_CONFIG_OPENROUTER_API_KEY": test_api_key}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.openrouter_api_key == test_api_key

    def test_openrouter_api_key_fallback_to_non_prefixed(self):
        """Test that openrouter_api_key falls back to OPENROUTER_API_KEY if prefixed not found."""
        test_api_key = "sk-or-v1-fallback123"
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": test_api_key}, clear=True):
            settings = Settings(_env_file=None)
            assert settings.openrouter_api_key == test_api_key

    def test_openrouter_api_key_prefixed_takes_precedence(self):
        """Test that prefixed env var takes precedence over non-prefixed."""
        prefixed_key = "sk-or-v1-prefixed123"
        non_prefixed_key = "sk-or-v1-nonprefixed456"
        with patch.dict(
            os.environ,
            {
                "CONNECTION_CONFIGS_CONFIG_OPENROUTER_API_KEY": prefixed_key,
                "OPENROUTER_API_KEY": non_prefixed_key,
            },
            clear=True
        ):
            settings = Settings(_env_file=None)
            assert settings.openrouter_api_key == prefixed_key

    def test_safe_addresses_loaded_from_prefixed_env_json(self):
        """Test that safe_addresses is loaded and parsed from CONNECTION_CONFIGS_CONFIG_SAFE_CONTRACT_ADDRESSES."""
        test_json = '{"base":"0x55196464De636b8ddA93Bdf78831b3aA0e429d60","ethereum":"0x123"}'
        with patch.dict(
            os.environ,
            {"CONNECTION_CONFIGS_CONFIG_SAFE_CONTRACT_ADDRESSES": test_json},
            clear=True
        ):
            settings = Settings(_env_file=None)
            assert settings.safe_addresses == {
                "base": "0x55196464De636b8ddA93Bdf78831b3aA0e429d60",
                "ethereum": "0x123"
            }
            assert isinstance(settings.safe_addresses, dict)

    def test_safe_addresses_auto_sets_base_safe_address(self):
        """Test that base_safe_address is auto-set from safe_addresses['base']."""
        test_json = '{"base":"0x55196464De636b8ddA93Bdf78831b3aA0e429d60"}'
        with patch.dict(
            os.environ,
            {"CONNECTION_CONFIGS_CONFIG_SAFE_CONTRACT_ADDRESSES": test_json},
            clear=True
        ):
            settings = Settings(_env_file=None)
            assert settings.base_safe_address == "0x55196464De636b8ddA93Bdf78831b3aA0e429d60"

    def test_multiple_prefixed_vars_loaded_together(self):
        """Test that multiple prefixed environment variables are loaded correctly."""
        env_vars = {
            "CONNECTION_CONFIGS_CONFIG_OPENROUTER_API_KEY": "sk-or-v1-test123",
            "CONNECTION_CONFIGS_CONFIG_SAFE_CONTRACT_ADDRESSES": '{"base":"0x123"}',
            "CONNECTION_CONFIGS_CONFIG_BASE_RPC_URL": "http://localhost:8545",
            "CONNECTION_CONFIGS_CONFIG_CHAIN_ID": "8453",
            "CONNECTION_CONFIGS_CONFIG_LOG_LEVEL": "DEBUG",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings(_env_file=None)
            assert settings.openrouter_api_key == "sk-or-v1-test123"
            assert settings.safe_addresses == {"base": "0x123"}
            assert settings.base_rpc_url == "http://localhost:8545"
            assert settings.chain_id == 8453
            assert settings.log_level == "DEBUG"

    def test_json_parsing_in_custom_settings_source(self):
        """Test that JSON strings are automatically parsed for dict/list fields."""
        json_addresses = '{"base":"0xABC","gnosis":"0xDEF"}'
        with patch.dict(
            os.environ,
            {"CONNECTION_CONFIGS_CONFIG_SAFE_CONTRACT_ADDRESSES": json_addresses},
            clear=True
        ):
            settings = Settings(_env_file=None)
            # Should be parsed as dict, not string
            assert isinstance(settings.safe_addresses, dict)
            assert settings.safe_addresses["base"] == "0xABC"
            assert settings.safe_addresses["gnosis"] == "0xDEF"


class TestPropertyMethods:
    """Test new property methods for agent configuration."""

    def test_monitored_daos_list_property_with_default(self):
        """Test that monitored_daos_list property returns default when no env var."""
        # Test without MONITORED_DAOS in environment
        env_backup = os.environ.get("MONITORED_DAOS")
        if "MONITORED_DAOS" in os.environ:
            del os.environ["MONITORED_DAOS"]
        try:
            settings = Settings(_env_file=None)
            expected = ["compound.eth", "nouns.eth", "arbitrum.eth"]
            assert settings.monitored_daos_list == expected
        finally:
            if env_backup is not None:
                os.environ["MONITORED_DAOS"] = env_backup

    def test_safe_addresses_dict_property_with_env_var(self):
        """Test that safe_addresses_dict property parses from environment variable."""
        test_addresses = "compound:0x123,nouns:0x456"
        with patch.dict(os.environ, {"SAFE_CONTRACT_ADDRESSES": test_addresses}):
            settings = Settings(_env_file=None)
            expected = {"compound": "0x123", "nouns": "0x456"}
            assert settings.safe_addresses_dict == expected

    def test_safe_addresses_dict_property_with_default(self):
        """Test that safe_addresses_dict property returns empty dict when no env var."""
        # Test without SAFE_CONTRACT_ADDRESSES in environment
        env_backup = os.environ.get("SAFE_CONTRACT_ADDRESSES")
        if "SAFE_CONTRACT_ADDRESSES" in os.environ:
            del os.environ["SAFE_CONTRACT_ADDRESSES"]
        try:
            settings = Settings(_env_file=None)
            expected = {}
            assert settings.safe_addresses_dict == expected
        finally:
            if env_backup is not None:
                os.environ["SAFE_CONTRACT_ADDRESSES"] = env_backup

    def test_safe_addresses_dict_property_with_malformed_data(self):
        """Test that safe_addresses_dict property handles malformed data gracefully."""
        test_addresses = "compound:0x123,invalid,nouns:0x456,also_invalid"
        with patch.dict(os.environ, {"SAFE_CONTRACT_ADDRESSES": test_addresses}):
            settings = Settings(_env_file=None)
            expected = {"compound": "0x123", "nouns": "0x456"}
            assert settings.safe_addresses_dict == expected

    def test_property_methods_return_types(self):
        """Test that property methods return correct types."""
        settings = Settings(_env_file=None)

        # Test return types
        assert isinstance(settings.monitored_daos_list, list)
        assert isinstance(settings.safe_addresses_dict, dict)

        # Test that all items in list are strings
        for dao in settings.monitored_daos_list:
            assert isinstance(dao, str)

        # Test that all dict keys and values are strings
        for key, value in settings.safe_addresses_dict.items():
            assert isinstance(key, str)
            assert isinstance(value, str)


