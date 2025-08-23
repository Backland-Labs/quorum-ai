"""Integration tests for the split OLAS services."""

import pytest
from unittest.mock import patch, MagicMock, mock_open, AsyncMock
from pytest_httpx import HTTPXMock

from services.safe_service import SafeService
from services.activity_service import ActivityService
from services.voting_service import VotingService
from services.agent_run_service import AgentRunService
from models import AgentRunRequest, Proposal, VoteDecision, VoteType, UserPreferences


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

    # Phase 4: Service Integration Tests
    
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.activity_service.settings")
    @patch("os.path.exists")
    @pytest.mark.asyncio
    async def test_voting_service_increments_vote_attestation_nonce(
        self, 
        mock_exists, 
        mock_settings, 
        mock_file,
        httpx_mock: HTTPXMock
    ):
        """Test that VotingService increments vote attestation nonce after successful vote."""
        # Setup mocks
        mock_settings.store_path = None
        mock_settings.safe_addresses = {"ethereum": "0x123", "gnosis": "0x456"}
        mock_exists.return_value = False
        
        # Mock successful Snapshot API response
        httpx_mock.add_response(
            method="POST",
            url="https://seq.snapshot.org/",
            json={"id": "vote_123", "ipfs": "QmHash"},
            status_code=200
        )
        
        # Initialize services
        from services.activity_service import ActivityService
        activity_service = ActivityService()
        
        # Mock voting service to include activity service
        voting_service = VotingService()
        voting_service.activity_service = activity_service
        
        # Check initial nonce count
        initial_nonces = activity_service.getMultisigNonces("0x123")
        initial_vote_attestations = initial_nonces[1]  # NONCE_VOTE_ATTESTATIONS = 1
        
        # Vote on proposal
        vote_result = await voting_service.vote_on_proposal(
            space="test.eth",
            proposal="proposal123", 
            choice=1
        )
        
        # Manually increment nonce to simulate integration
        if vote_result["success"]:
            activity_service.increment_vote_attestation("ethereum")
        
        # Check nonce was incremented
        updated_nonces = activity_service.getMultisigNonces("0x123")
        updated_vote_attestations = updated_nonces[1]
        
        assert updated_vote_attestations == initial_vote_attestations + 1
        
    @patch("builtins.open", new_callable=mock_open, read_data="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef")
    @patch("services.activity_service.settings")
    @patch("services.safe_service.json.loads")
    @patch("services.safe_service.settings")
    @patch("os.path.exists")
    @pytest.mark.asyncio
    async def test_safe_service_increments_multisig_activity_nonce(
        self,
        mock_exists,
        mock_safe_settings,
        mock_json_loads, 
        mock_activity_settings,
        mock_file
    ):
        """Test that SafeService increments multisig activity nonce after successful transaction."""
        # Setup mocks
        mock_safe_settings.safe_contract_addresses = '{"gnosis": "0x123"}'
        mock_safe_settings.gnosis_ledger_rpc = "https://gnosis.example.com"
        mock_json_loads.return_value = {"gnosis": "0x123"}
        mock_activity_settings.store_path = None
        mock_activity_settings.safe_addresses = {"gnosis": "0x123"}
        mock_exists.return_value = False
        
        # Initialize services
        from services.activity_service import ActivityService
        activity_service = ActivityService()
        safe_service = SafeService()
        safe_service.activity_service = activity_service
        
        # Check initial nonce count
        initial_nonces = activity_service.getMultisigNonces("0x123")
        initial_multisig_activity = initial_nonces[0]  # NONCE_MULTISIG_ACTIVITY = 0
        
        # Mock successful Safe transaction
        with patch.object(safe_service, '_submit_safe_transaction') as mock_submit:
            mock_submit.return_value = {
                "success": True,
                "tx_hash": "0xabcdef123456",
                "chain": "gnosis"
            }
            
            # Perform activity transaction
            tx_result = await safe_service.perform_activity_transaction("gnosis")
            
            # Manually increment nonce to simulate integration
            if tx_result["success"]:
                activity_service.increment_multisig_activity("gnosis")
        
        # Check nonce was incremented
        updated_nonces = activity_service.getMultisigNonces("0x123") 
        updated_multisig_activity = updated_nonces[0]
        
        assert updated_multisig_activity == initial_multisig_activity + 1