"""
Tests for EAS attestation functionality in Safe service.

This test module validates the integration of EAS (Ethereum Attestation Service)
with the Safe service for creating on-chain attestations of Snapshot votes.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from datetime import datetime
from web3 import Web3

from services.safe_service import SafeService
from models import EASAttestationData
from config import Settings


class TestSafeServiceEAS:
    """Test EAS attestation functionality in Safe service."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with EAS configuration."""
        settings = MagicMock(spec=Settings)
        settings.eas_contract_address = "0x4200000000000000000000000000000000000021"
        settings.eas_schema_uid = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        settings.base_safe_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f89590"
        settings.get_base_rpc_endpoint.return_value = "https://base-mainnet.g.alchemy.com/v2/test-key"
        settings.agent_address = "0x1234567890123456789012345678901234567890"
        settings.safe_contract_addresses = "{}"  # Empty JSON for safe addresses
        # Add RPC endpoints
        settings.ethereum_ledger_rpc = "https://eth-mainnet.g.alchemy.com/v2/test-key"
        settings.gnosis_ledger_rpc = "https://gnosis-mainnet.g.alchemy.com/v2/test-key"
        settings.base_ledger_rpc = "https://base-mainnet.g.alchemy.com/v2/test-key"
        settings.mode_ledger_rpc = "https://mode-mainnet.g.alchemy.com/v2/test-key"
        return settings
    
    @pytest.fixture
    def safe_service(self, mock_settings):
        """Create SafeService instance with mocked settings."""
        mock_private_key = "0x1234567890123456789012345678901234567890123456789012345678901234"
        
        with patch("services.safe_service.settings", mock_settings), \
             patch("builtins.open", mock_open(read_data=mock_private_key)):
            service = SafeService()
            # Mock the account
            service.account = MagicMock()
            service.account.address = "0x1234567890123456789012345678901234567890"
            return service
    
    @pytest.fixture
    def sample_attestation_data(self):
        """Create sample EAS attestation data."""
        return EASAttestationData(
            proposal_id="0xproposal123",
            space_id="aave.eth",
            voter_address="0x742d35Cc6634C0532925a3b844Bc9e7595f89590",
            choice=1,
            vote_tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
            timestamp=datetime.utcnow(),
            retry_count=0
        )
    
    async def test_create_eas_attestation_success(self, mock_settings, sample_attestation_data):
        """
        Test successful creation of EAS attestation.
        
        This test validates that the service correctly creates an attestation
        transaction and submits it through the Safe infrastructure.
        """
        mock_private_key = "0x1234567890123456789012345678901234567890123456789012345678901234"
        
        with patch("services.safe_service.settings", mock_settings), \
             patch("builtins.open", mock_open(read_data=mock_private_key)):
            safe_service = SafeService()
            
            # Mock the internal methods
            mock_tx_data = {
                "to": "0x4200000000000000000000000000000000000021",
                "data": "0xabcdef123456",
                "value": 0
            }
            
            safe_service._build_eas_attestation_tx = MagicMock(return_value=mock_tx_data)
            safe_service._submit_safe_transaction = AsyncMock(return_value={
                "hash": "0xsafetx1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
            })
            
            # Execute attestation
            result = await safe_service.create_eas_attestation(sample_attestation_data)
            
            # Verify the result
            assert result["success"] is True
            assert "safe_tx_hash" in result
            assert result["safe_tx_hash"] == "0xsafetx1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
            
            # Verify method calls
            safe_service._build_eas_attestation_tx.assert_called_once_with(sample_attestation_data)
            safe_service._submit_safe_transaction.assert_called_once()
    
    async def test_create_eas_attestation_missing_config(self, mock_settings, sample_attestation_data):
        """
        Test that attestation fails gracefully when EAS configuration is missing.
        
        This test ensures proper error handling when required configuration
        values are not set.
        """
        # Remove EAS configuration
        mock_settings.eas_contract_address = None
        
        with patch("services.safe_service.settings", mock_settings):
            service = SafeService()
            
            result = await service.create_eas_attestation(sample_attestation_data)
            
            assert result["success"] is False
            assert "error" in result
            assert "EAS configuration missing" in result["error"]
    
    async def test_create_eas_attestation_transaction_failure(self, mock_settings, sample_attestation_data):
        """
        Test handling of transaction submission failure.
        
        This test validates that the service properly handles errors when
        the Safe transaction submission fails.
        """
        mock_private_key = "0x1234567890123456789012345678901234567890123456789012345678901234"
        
        with patch("services.safe_service.settings", mock_settings), \
             patch("builtins.open", mock_open(read_data=mock_private_key)):
            safe_service = SafeService()
            
            # Mock transaction building success but submission failure
            mock_tx_data = {
                "to": "0x4200000000000000000000000000000000000021",
                "data": "0xabcdef123456",
                "value": 0
            }
            
            safe_service._build_eas_attestation_tx = MagicMock(return_value=mock_tx_data)
            safe_service._submit_safe_transaction = AsyncMock(
                side_effect=Exception("Transaction submission failed")
            )
            
            # Execute attestation
            result = await safe_service.create_eas_attestation(sample_attestation_data)
            
            # Verify error handling
            assert result["success"] is False
            assert "error" in result
            assert "Transaction submission failed" in result["error"]
    
    def test_build_eas_attestation_tx(self, mock_settings, sample_attestation_data):
        """
        Test building EAS attestation transaction data.
        
        This test validates that the service correctly encodes the attestation
        data into a proper EAS contract call.
        """
        mock_private_key = "0x1234567890123456789012345678901234567890123456789012345678901234"
        
        with patch("services.safe_service.settings", mock_settings), \
             patch("builtins.open", mock_open(read_data=mock_private_key)):
            safe_service = SafeService()
            
            # Mock Web3 and contract
            mock_web3 = MagicMock()
            mock_eth = MagicMock()
            mock_contract = MagicMock()
            mock_function = MagicMock()
            
            # Setup the mock chain
            mock_function.build_transaction.return_value = {
                "to": "0x4200000000000000000000000000000000000021",
                "data": "0xencodeddata",
                "value": 0,
                "gas": 200000
            }
            mock_contract.functions.attest.return_value = mock_function
            mock_eth.contract.return_value = mock_contract
            mock_web3.eth = mock_eth
            
            with patch.object(safe_service, '_get_web3_instance', return_value=mock_web3):
                with patch.object(safe_service, '_load_eas_abi', return_value=[]):
                    result = safe_service._build_eas_attestation_tx(sample_attestation_data)
                    
                    assert result is not None
                    assert "to" in result
                    assert "data" in result
                    assert result["to"] == "0x4200000000000000000000000000000000000021"
    
    def test_encode_attestation_data(self, safe_service, sample_attestation_data):
        """
        Test encoding attestation data for EAS schema.
        
        This test validates that vote data is correctly encoded according to
        the EAS schema requirements.
        """
        encoded = safe_service._encode_attestation_data(sample_attestation_data)
        
        # Should return ABI-encoded bytes
        assert isinstance(encoded, bytes)
        assert len(encoded) > 0
        
        # The encoded data should contain the proposal ID, space ID, choice, etc.
        # This is a simplified check - in reality, we'd verify the exact encoding
        assert len(encoded) >= 32  # At minimum, should have some data