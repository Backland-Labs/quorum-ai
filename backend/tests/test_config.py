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