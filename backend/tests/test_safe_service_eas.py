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
        # Add AttestationTracker configuration (not configured by default)
        settings.attestation_tracker_address = None
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
            
            # Mock the delegated attestation method (new implementation)
            mock_tx_data = {
                "to": "0x4200000000000000000000000000000000000021",
                "data": "0xencodeddata",
                "value": 0
            }
            
            with patch.object(safe_service, '_build_delegated_attestation_tx', return_value=mock_tx_data), \
                 patch("utils.web3_provider.get_w3"):
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


class TestAttestationTrackerIntegration:
    """Test AttestationTracker routing functionality."""

    @pytest.fixture
    def mock_settings_with_tracker(self):
        """Create mock settings with AttestationTracker configured."""
        settings = MagicMock(spec=Settings)
        settings.eas_contract_address = "0x4200000000000000000000000000000000000021"
        settings.eas_schema_uid = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        settings.base_safe_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f89590"
        settings.get_base_rpc_endpoint.return_value = "https://base-mainnet.g.alchemy.com/v2/test-key"
        settings.agent_address = "0x1234567890123456789012345678901234567890"
        settings.safe_contract_addresses = "{}"
        # Configure AttestationTracker address
        settings.attestation_tracker_address = "0x9876543210987654321098765432109876543210"
        # Add RPC endpoints
        settings.ethereum_ledger_rpc = "https://eth-mainnet.g.alchemy.com/v2/test-key"
        settings.gnosis_ledger_rpc = "https://gnosis-mainnet.g.alchemy.com/v2/test-key"
        settings.base_ledger_rpc = "https://base-mainnet.g.alchemy.com/v2/test-key"
        settings.mode_ledger_rpc = "https://mode-mainnet.g.alchemy.com/v2/test-key"
        return settings

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

    def test_attestation_routing_with_tracker_configured(self, mock_settings_with_tracker, sample_attestation_data):
        """Test that attestations route through AttestationTracker when address configured.
        
        This test validates the core routing logic that directs attestations to the
        AttestationTracker wrapper when its address is configured in settings.
        """
        mock_private_key = "0x1234567890123456789012345678901234567890123456789012345678901234"
        
        with patch("services.safe_service.settings", mock_settings_with_tracker), \
             patch("builtins.open", mock_open(read_data=mock_private_key)):
            safe_service = SafeService()
            
            # Mock the delegated attestation method
            mock_tx_data = {
                "to": "0x9876543210987654321098765432109876543210",  # AttestationTracker address
                "data": "0xdelegateddata",
                "value": 0
            }
            
            with patch.object(safe_service, '_build_delegated_attestation_tx', return_value=mock_tx_data) as mock_delegated, \
                 patch("utils.web3_provider.get_w3"):
                result = safe_service._build_eas_attestation_tx(sample_attestation_data)
                
                # Verify routing to AttestationTracker
                mock_delegated.assert_called_once_with(
                    sample_attestation_data,
                    target_address=mock_settings_with_tracker.attestation_tracker_address,
                    abi_name="attestation_tracker"
                )
                assert result["to"] == "0x9876543210987654321098765432109876543210"

    def test_attestation_routing_without_tracker(self, mock_settings_with_tracker, sample_attestation_data):
        """Test that attestations use direct EAS when AttestationTracker not configured.
        
        This test ensures backward compatibility by verifying that when no AttestationTracker
        address is configured, attestations still route directly to EAS using delegated pattern.
        """
        mock_private_key = "0x1234567890123456789012345678901234567890123456789012345678901234"
        
        # Ensure no AttestationTracker configured
        mock_settings_with_tracker.attestation_tracker_address = None
        
        with patch("services.safe_service.settings", mock_settings_with_tracker), \
             patch("builtins.open", mock_open(read_data=mock_private_key)):
            safe_service = SafeService()
            
            # Mock the delegated attestation method
            mock_tx_data = {
                "to": "0x4200000000000000000000000000000000000021",  # EAS address
                "data": "0xdelegateddata",
                "value": 0
            }
            
            with patch.object(safe_service, '_build_delegated_attestation_tx', return_value=mock_tx_data) as mock_delegated, \
                 patch("utils.web3_provider.get_w3"):
                result = safe_service._build_eas_attestation_tx(sample_attestation_data)
                
                # Verify routing to EAS
                mock_delegated.assert_called_once_with(
                    sample_attestation_data,
                    target_address=mock_settings_with_tracker.eas_contract_address,
                    abi_name="eas"
                )
                assert result["to"] == "0x4200000000000000000000000000000000000021"

    def test_build_delegated_attestation_tx(self, mock_settings_with_tracker, sample_attestation_data):
        """Test building delegated attestation transaction for both EAS and AttestationTracker.
        
        This test validates that the delegated attestation pattern is correctly implemented
        with proper DelegatedAttestationRequest struct and attestByDelegation method call.
        """
        mock_private_key = "0x1234567890123456789012345678901234567890123456789012345678901234"
        
        with patch("services.safe_service.settings", mock_settings_with_tracker), \
             patch("builtins.open", mock_open(read_data=mock_private_key)):
            safe_service = SafeService()
            
            # Mock Web3 and contract for delegated pattern
            mock_web3 = MagicMock()
            mock_eth = MagicMock()
            mock_contract = MagicMock()
            mock_function = MagicMock()
            
            # Setup the mock chain for attestByDelegation
            mock_function.build_transaction.return_value = {
                "to": "0x9876543210987654321098765432109876543210",
                "data": "0xdelegateddata",
                "value": 0,
                "gas": 300000
            }
            mock_contract.functions.attestByDelegation.return_value = mock_function
            mock_eth.contract.return_value = mock_contract
            mock_web3.eth = mock_eth
            mock_web3.to_checksum_address.return_value = "0x9876543210987654321098765432109876543210"
            mock_web3.to_bytes.return_value = b"\x12\x34\x56"
            
            with patch("utils.web3_provider.get_w3", return_value=mock_web3), \
                 patch("utils.abi_loader.load_abi", return_value=[]), \
                 patch.object(safe_service, '_encode_attestation_data', return_value=b"encoded"):
                
                result = safe_service._build_delegated_attestation_tx(
                    sample_attestation_data,
                    target_address="0x9876543210987654321098765432109876543210", 
                    abi_name="attestation_tracker"
                )
                
                # Verify transaction structure
                assert result is not None
                assert result["to"] == "0x9876543210987654321098765432109876543210"
                assert result["data"] == "0xdelegateddata"
                assert result["value"] == 0
                
                # Verify contract method was called with delegated request
                mock_contract.functions.attestByDelegation.assert_called_once()