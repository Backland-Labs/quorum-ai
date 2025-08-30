"""Tests for AttestationTracker monitoring helper functions.

These tests verify the core business logic for querying AttestationTracker
contract statistics and graceful error handling.
"""

import pytest
from unittest.mock import patch, MagicMock
from web3 import Web3
from utils.attestation_tracker_helpers import (
    get_multisig_info,
    get_attestation_count,
)


class TestAttestationTrackerHelpers:
    """Test AttestationTracker monitoring helper functions."""

    @patch("utils.attestation_tracker_helpers.settings")
    @patch("utils.attestation_tracker_helpers.get_w3")
    @patch("utils.attestation_tracker_helpers.load_abi")
    def test_get_multisig_info_success(self, mock_load_abi, mock_get_w3, mock_settings):
        """Test successful multisig info retrieval from AttestationTracker."""
        # Setup mocks with valid hex addresses
        mock_settings.attestation_tracker_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f89590"
        mock_contract = MagicMock()
        mock_contract.functions.multisigStats.return_value.call.return_value = (
            1 << 255 | 5  # Active status (MSB=1) + count of 5
        )
        
        mock_w3 = MagicMock()
        mock_w3.eth.contract.return_value = mock_contract
        mock_get_w3.return_value = mock_w3
        
        mock_load_abi.return_value = [{"name": "multisigStats"}]
        
        # Test with valid address
        count, is_active = get_multisig_info("0x742d35Cc6634C0532925a3b844Bc9e7595f89591")
        
        # Verify
        assert count == 5
        assert is_active == True
        mock_contract.functions.multisigStats.assert_called_once_with("0x742d35Cc6634C0532925a3b844Bc9e7595f89591")

    @patch("utils.attestation_tracker_helpers.settings")
    def test_get_multisig_info_no_tracker_configured(self, mock_settings):
        """Test graceful fallback when AttestationTracker not configured."""
        # Setup - no tracker address
        mock_settings.attestation_tracker_address = None
        
        # Test
        count, is_active = get_multisig_info("0x742d35Cc6634C0532925a3b844Bc9e7595f89591")
        
        # Verify graceful defaults
        assert count == 0
        assert is_active == False

    @patch("utils.attestation_tracker_helpers.settings")
    @patch("utils.attestation_tracker_helpers.get_w3")
    def test_get_multisig_info_contract_error(self, mock_get_w3, mock_settings):
        """Test graceful error handling when contract call fails."""
        # Setup - tracker configured but contract call fails
        mock_settings.attestation_tracker_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f89590"
        mock_get_w3.side_effect = Exception("Web3 connection failed")
        
        # Test
        count, is_active = get_multisig_info("0x742d35Cc6634C0532925a3b844Bc9e7595f89591")
        
        # Verify graceful fallback
        assert count == 0
        assert is_active == False