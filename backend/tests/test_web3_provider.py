"""Tests for Web3 provider utility."""

import pytest
from unittest.mock import Mock, patch
from web3 import Web3

from utils.web3_provider import get_w3


class TestWeb3Provider:
    """Test Web3 provider utility functionality."""
    
    def test_get_w3_base_chain_returns_connected_instance(self):
        """Test that get_w3 returns a connected Web3 instance for base chain."""
        with patch('utils.web3_provider.settings') as mock_settings:
            mock_settings.get_base_rpc_endpoint.return_value = "https://base-mainnet.g.alchemy.com/v2/test"
            
            with patch('utils.web3_provider.Web3') as mock_web3_class:
                mock_web3_instance = Mock()
                mock_web3_instance.is_connected.return_value = True
                mock_web3_class.return_value = mock_web3_instance
                
                result = get_w3("base")
                
                assert result == mock_web3_instance
                mock_web3_class.assert_called_once()
    
    def test_get_w3_raises_error_for_unknown_chain(self):
        """Test that get_w3 raises ValueError for unsupported chains."""
        with pytest.raises(ValueError, match="No RPC endpoint configured for chain: unknown"):
            get_w3("unknown")
    
    def test_get_w3_raises_error_when_no_rpc_configured(self):
        """Test that get_w3 raises ValueError when no RPC endpoint is configured."""
        with patch('utils.web3_provider.settings') as mock_settings:
            mock_settings.get_base_rpc_endpoint.return_value = None
            mock_settings.ethereum_ledger_rpc = None
            
            with pytest.raises(ValueError, match="No RPC endpoint configured for chain: base"):
                get_w3("base")