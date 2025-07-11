"""Test configuration settings for Olas Agent Architecture."""

import os
import pytest
from unittest.mock import patch

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

    def test_safe_addresses_defaults_to_empty_dict(self):
        """Test that safe_addresses defaults to empty dict."""
        settings = Settings()
        assert settings.safe_addresses == {}
        assert isinstance(settings.safe_addresses, dict)

    def test_safe_addresses_loaded_from_env(self):
        """Test that safe_addresses is loaded from SAFE_CONTRACT_ADDRESSES environment variable."""
        test_addresses = "dao1:0x123,dao2:0x456"
        with patch.dict(os.environ, {"SAFE_CONTRACT_ADDRESSES": test_addresses}):
            settings = Settings()
            expected = {"dao1": "0x123", "dao2": "0x456"}
            assert settings.safe_addresses == expected

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
        with patch.dict(os.environ, {"SAFE_CONTRACT_ADDRESSES": "dao1: 0x123 , dao2: 0x456 "}):
            settings = Settings()
            expected = {"dao1": "0x123", "dao2": "0x456"}
            assert settings.safe_addresses == expected

        # Test with empty values
        with patch.dict(os.environ, {"SAFE_CONTRACT_ADDRESSES": "dao1:0x123,,dao2:0x456"}):
            settings = Settings()
            expected = {"dao1": "0x123", "dao2": "0x456"}
            assert settings.safe_addresses == expected

        # Test with malformed entries
        with patch.dict(os.environ, {"SAFE_CONTRACT_ADDRESSES": "dao1:0x123,invalid,dao2:0x456"}):
            settings = Settings()
            expected = {"dao1": "0x123", "dao2": "0x456"}
            assert settings.safe_addresses == expected


class TestAgentSpecificSettings:
    """Test agent-specific configuration settings."""

    def test_monitored_daos_defaults_to_empty_list(self):
        """Test that monitored_daos defaults to empty list."""
        settings = Settings()
        assert settings.monitored_daos == []
        assert isinstance(settings.monitored_daos, list)

    def test_monitored_daos_loaded_from_env(self):
        """Test that monitored_daos can be parsed from string."""
        # Test the field validator directly
        result = Settings.parse_monitored_daos("compound.eth,nouns.eth,arbitrum.eth")
        expected = ["compound.eth", "nouns.eth", "arbitrum.eth"]
        assert result == expected

    def test_vote_confidence_threshold_defaults_to_0_6(self):
        """Test that vote_confidence_threshold defaults to 0.6."""
        settings = Settings()
        assert settings.vote_confidence_threshold == 0.6

    def test_vote_confidence_threshold_loaded_from_env(self):
        """Test that vote_confidence_threshold is loaded from environment variable."""
        test_threshold = 0.8
        with patch.dict(os.environ, {"VOTE_CONFIDENCE_THRESHOLD": str(test_threshold)}):
            settings = Settings()
            assert settings.vote_confidence_threshold == test_threshold

    def test_vote_confidence_threshold_validation(self):
        """Test that vote_confidence_threshold is validated between 0.0 and 1.0."""
        # Test valid values
        valid_values = [0.0, 0.1, 0.5, 0.9, 1.0]
        for value in valid_values:
            with patch.dict(os.environ, {"VOTE_CONFIDENCE_THRESHOLD": str(value)}):
                settings = Settings()
                assert settings.vote_confidence_threshold == value

        # Test invalid values should raise validation error
        invalid_values = [-0.1, 1.1, 2.0]
        for value in invalid_values:
            with patch.dict(os.environ, {"VOTE_CONFIDENCE_THRESHOLD": str(value)}):
                with pytest.raises(ValueError):
                    Settings()

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

    def test_monitored_daos_parsing_edge_cases(self):
        """Test monitored_daos parsing with edge cases."""
        # Test with spaces
        result = Settings.parse_monitored_daos("compound.eth, nouns.eth , arbitrum.eth ")
        expected = ["compound.eth", "nouns.eth", "arbitrum.eth"]
        assert result == expected

        # Test with empty values
        result = Settings.parse_monitored_daos("compound.eth,,nouns.eth")
        expected = ["compound.eth", "nouns.eth"]
        assert result == expected

        # Test with single value
        result = Settings.parse_monitored_daos("compound.eth")
        expected = ["compound.eth"]
        assert result == expected

        # Test with empty string
        result = Settings.parse_monitored_daos("")
        expected = []
        assert result == expected

        # Test with None
        result = Settings.parse_monitored_daos(None)
        expected = []
        assert result == expected

        # Test with list (pass-through)
        test_list = ["compound.eth", "nouns.eth"]
        result = Settings.parse_monitored_daos(test_list)
        assert result == test_list


class TestOlasStakingConfiguration:
    """Test Olas staking configuration settings."""

    def test_staking_token_contract_address_defaults_to_none(self):
        """Test that staking_token_contract_address defaults to None."""
        settings = Settings()
        assert settings.staking_token_contract_address is None

    def test_staking_token_contract_address_loaded_from_env(self):
        """Test that staking_token_contract_address is loaded from environment variable."""
        test_address = "0x123456789abcdef"
        with patch.dict(os.environ, {"STAKING_TOKEN_CONTRACT_ADDRESS": test_address}):
            settings = Settings()
            assert settings.staking_token_contract_address == test_address

    def test_activity_checker_contract_address_defaults_to_none(self):
        """Test that activity_checker_contract_address defaults to None."""
        settings = Settings()
        assert settings.activity_checker_contract_address is None

    def test_activity_checker_contract_address_loaded_from_env(self):
        """Test that activity_checker_contract_address is loaded from environment variable."""
        test_address = "0x987654321fedcba"
        with patch.dict(os.environ, {"ACTIVITY_CHECKER_CONTRACT_ADDRESS": test_address}):
            settings = Settings()
            assert settings.activity_checker_contract_address == test_address

    def test_service_registry_token_utility_contract_defaults_to_none(self):
        """Test that service_registry_token_utility_contract defaults to None."""
        settings = Settings()
        assert settings.service_registry_token_utility_contract is None

    def test_service_registry_token_utility_contract_loaded_from_env(self):
        """Test that service_registry_token_utility_contract is loaded from environment variable."""
        test_address = "0xabcdef123456789"
        with patch.dict(os.environ, {"SERVICE_REGISTRY_TOKEN_UTILITY_CONTRACT": test_address}):
            settings = Settings()
            assert settings.service_registry_token_utility_contract == test_address

    def test_all_staking_contracts_loaded_together(self):
        """Test that all staking contract addresses can be loaded together."""
        test_staking = "0x111111111111111"
        test_activity = "0x222222222222222"
        test_registry = "0x333333333333333"
        
        env_vars = {
            "STAKING_TOKEN_CONTRACT_ADDRESS": test_staking,
            "ACTIVITY_CHECKER_CONTRACT_ADDRESS": test_activity,
            "SERVICE_REGISTRY_TOKEN_UTILITY_CONTRACT": test_registry,
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.staking_token_contract_address == test_staking
            assert settings.activity_checker_contract_address == test_activity
            assert settings.service_registry_token_utility_contract == test_registry

    def test_staking_contract_addresses_validation(self):
        """Test that contract addresses can be empty strings."""
        with patch.dict(os.environ, {"STAKING_TOKEN_CONTRACT_ADDRESS": ""}):
            settings = Settings()
            assert settings.staking_token_contract_address == ""

    def test_staking_contract_addresses_are_optional(self):
        """Test that all staking contract addresses are optional."""
        settings = Settings()
        
        # All should be None by default
        assert settings.staking_token_contract_address is None
        assert settings.activity_checker_contract_address is None
        assert settings.service_registry_token_utility_contract is None
        
        # Should be able to create settings without any staking config
        assert isinstance(settings, Settings)


class TestPropertyMethods:
    """Test new property methods for agent configuration."""

    def test_monitored_daos_list_property_with_env_var(self):
        """Test that monitored_daos_list property parses from environment variable."""
        # Test the property logic directly by mocking os.getenv for specific calls
        test_daos = "test1.eth,test2.eth,test3.eth"
        settings = Settings(_env_file=None)
        
        def mock_getenv(key, default=""):
            if key == "MONITORED_DAOS":
                return test_daos
            return os.getenv(key, default)
        
        with patch('config.os.getenv', side_effect=mock_getenv):
            expected = ["test1.eth", "test2.eth", "test3.eth"]
            result = settings.monitored_daos_list
            assert result == expected

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

    def test_monitored_daos_list_property_with_spaces_and_empty(self):
        """Test that monitored_daos_list property handles spaces and empty values."""
        test_daos = " compound.eth , , nouns.eth , arbitrum.eth "
        settings = Settings(_env_file=None)
        
        def mock_getenv(key, default=""):
            if key == "MONITORED_DAOS":
                return test_daos
            return os.getenv(key, default)
        
        with patch('config.os.getenv', side_effect=mock_getenv):
            expected = ["compound.eth", "nouns.eth", "arbitrum.eth"]
            result = settings.monitored_daos_list
            assert result == expected

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

    def test_monitored_daos_list_property_with_empty_string(self):
        """Test that monitored_daos_list property handles empty string."""
        with patch('config.os.getenv') as mock_getenv:
            mock_getenv.return_value = ""
            settings = Settings(_env_file=None)
            # When empty, should fall back to default
            expected = ["compound.eth", "nouns.eth", "arbitrum.eth"]
            result = settings.monitored_daos_list
            assert result == expected