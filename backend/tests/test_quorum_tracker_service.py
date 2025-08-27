"""Tests for QuorumTrackerService."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from services.quorum_tracker_service import QuorumTrackerService
from services.safe_service import SafeService
from models import ActivityType


@pytest.fixture
def mock_safe_service():
    """Create a mock SafeService for testing."""
    mock = Mock(spec=SafeService)
    mock._submit_safe_transaction = AsyncMock()
    return mock


@pytest.fixture
def quorum_tracker_service(mock_safe_service):
    """Create QuorumTrackerService with mocked dependencies."""
    return QuorumTrackerService(mock_safe_service)


class TestQuorumTrackerService:
    """Test QuorumTrackerService functionality."""

    @pytest.mark.asyncio
    async def test_register_activity_success(self, quorum_tracker_service, mock_safe_service):
        """Test successful activity registration."""
        # Arrange
        multisig_address = "0x1234567890123456789012345678901234567890"
        activity_type = ActivityType.VOTE_CAST
        
        mock_safe_service._submit_safe_transaction.return_value = {
            "success": True,
            "tx_hash": "0xabc123",
            "chain": "base"
        }

        with patch('services.quorum_tracker_service.settings') as mock_settings, \
             patch('services.quorum_tracker_service.Web3') as mock_web3:
            mock_settings.quorum_tracker_address = "0x9999999999999999999999999999999999999999"
            
            # Mock Web3 contract creation
            mock_contract = Mock()
            mock_contract.functions.register.return_value.build_transaction.return_value = {
                "data": "0x1234"
            }
            mock_web3.return_value.eth.contract.return_value = mock_contract
            mock_web3.to_checksum_address.side_effect = lambda x: x
            
            # Act
            result = await quorum_tracker_service.register_activity(
                multisig_address, activity_type
            )

            # Assert
            assert result["success"] is True
            assert "tx_hash" in result
            assert result["activity_type"] == activity_type
            assert result["multisig_address"] == multisig_address
            mock_safe_service._submit_safe_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_activity_no_contract_address(self, quorum_tracker_service):
        """Test activity registration fails when contract address not configured."""
        # Arrange
        multisig_address = "0x1234567890123456789012345678901234567890"
        activity_type = ActivityType.VOTE_CAST

        with patch('services.quorum_tracker_service.settings') as mock_settings:
            mock_settings.quorum_tracker_address = None
            
            # Act
            result = await quorum_tracker_service.register_activity(
                multisig_address, activity_type
            )

            # Assert
            assert result["success"] is False
            assert "QuorumTracker contract address not configured" in result["error"]

    def test_register_activity_invalid_inputs(self, quorum_tracker_service):
        """Test activity registration validates input parameters."""
        # Test empty multisig address
        with pytest.raises(AssertionError):
            import asyncio
            asyncio.run(quorum_tracker_service.register_activity("", 0))
            
        # Test invalid activity type
        with pytest.raises(AssertionError):
            import asyncio
            asyncio.run(quorum_tracker_service.register_activity(
                "0x1234567890123456789012345678901234567890", 5
            ))