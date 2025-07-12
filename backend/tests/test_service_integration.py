"""Integration tests for the split OLAS services."""

import pytest
from unittest.mock import patch, MagicMock, mock_open
from pytest_httpx import HTTPXMock

from services.safe_service import SafeService
from services.activity_service import ActivityService
from services.voting_service import VotingService


class TestServiceIntegration:
    """Test integration between split services."""
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_services_can_be_initialized_together(
        self, 
        mock_exists, 
        mock_activity_settings, 
        mock_safe_settings, 
        mock_json_loads, 
        mock_file
    ):
        """Test that all three services can be initialized together."""
        # Setup mocks
        mock_safe_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_safe_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        mock_activity_settings.store_path = None
        mock_exists.return_value = False
        
        # Initialize services
        safe_service = SafeService()
        activity_service = ActivityService()
        voting_service = VotingService()
        
        # Verify they were created successfully
        assert safe_service is not None
        assert activity_service is not None
        assert voting_service is not None
        assert safe_service.account.address == voting_service.account.address
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    @pytest.mark.asyncio
    async def test_activity_service_can_trigger_safe_transaction(
        self, 
        mock_exists, 
        mock_activity_settings, 
        mock_safe_settings, 
        mock_json_loads, 
        mock_file
    ):
        """Test that ActivityService can request SafeService to create transactions."""
        # Setup mocks
        mock_safe_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_safe_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        mock_activity_settings.store_path = None
        mock_exists.return_value = False
        
        # Initialize services
        safe_service = SafeService()
        activity_service = ActivityService()
        
        # Mock the SafeService transaction method
        with patch.object(safe_service, 'perform_activity_transaction') as mock_transaction:
            mock_transaction.return_value = {
                "success": True,
                "tx_hash": "0xabcdef123456",
                "chain": "gnosis"
            }
            
            # Test the integration through ensure_daily_compliance
            result = await activity_service.ensure_daily_compliance(safe_service)
            
            # Verify interaction
            assert result["success"] is True
            assert result["action_taken"] == "safe_transaction"
            mock_transaction.assert_called_once()
            
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    @pytest.mark.asyncio
    async def test_complete_workflow_voting_and_activity(
        self, 
        mock_exists, 
        mock_settings, 
        mock_file,
        httpx_mock: HTTPXMock
    ):
        """Test complete workflow: voting + activity tracking."""
        # Setup mocks
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        # Mock successful Snapshot API response
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            json={"id": "vote_123", "ipfs": "QmHash"},
            status_code=200
        )
        
        # Initialize services
        voting_service = VotingService()
        activity_service = ActivityService()
        
        # Step 1: Vote on a proposal
        vote_result = await voting_service.vote_on_proposal(
            space="test.eth",
            proposal="proposal123",
            choice=1
        )
        
        assert vote_result["success"] is True
        assert "tx_hash" not in vote_result  # Voting doesn't create blockchain tx
        
        # Step 2: Check if activity is needed (should be true initially)
        compliance_status = activity_service.check_olas_compliance()
        assert compliance_status["compliant"] is False
        
        # Step 3: Simulate marking activity as completed
        activity_service.mark_activity_completed("0xabcdef123456")
        
        # Step 4: Verify compliance is now satisfied
        updated_compliance = activity_service.check_olas_compliance()
        assert updated_compliance["compliant"] is True
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_services_share_same_account(
        self, 
        mock_exists, 
        mock_activity_settings, 
        mock_safe_settings, 
        mock_json_loads, 
        mock_file
    ):
        """Test that SafeService and VotingService use the same EOA account."""
        # Setup mocks
        mock_safe_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_safe_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        mock_activity_settings.store_path = None
        mock_exists.return_value = False
        
        # Initialize services
        safe_service = SafeService()
        voting_service = VotingService()
        
        # Both services should use the same account from the same private key file
        assert safe_service.account.address == voting_service.account.address
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    def test_activity_service_provides_status_for_monitoring(
        self, 
        mock_exists, 
        mock_settings, 
        mock_file
    ):
        """Test that ActivityService provides comprehensive status for monitoring."""
        mock_settings.store_path = None
        mock_exists.return_value = False
        
        activity_service = ActivityService()
        
        # Get initial status (no activity)
        initial_status = activity_service.get_compliance_summary()
        
        assert "activity_status" in initial_status
        assert "olas_compliance" in initial_status
        assert initial_status["activity_status"]["daily_activity_needed"] is True
        assert initial_status["olas_compliance"]["compliant"] is False
        
        # Mark activity completed
        activity_service.mark_activity_completed("0xtest")
        
        # Get updated status
        updated_status = activity_service.get_compliance_summary()
        assert updated_status["activity_status"]["daily_activity_needed"] is False
        assert updated_status["olas_compliance"]["compliant"] is True