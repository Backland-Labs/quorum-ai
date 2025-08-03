"""
Test attestation integration in agent run service.

This test file verifies that EAS attestations are properly queued
and processed after successful Snapshot votes, ensuring the integration
is non-blocking and handles failures gracefully.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from services.agent_run_service import AgentRunService
from models import (
    VoteDecision, VotingStrategy, 
    UserPreferences, EASAttestationData
)


@pytest.fixture
def mock_services():
    """Mock all external services used by agent run service."""
    with patch('services.agent_run_service.SnapshotService') as mock_snapshot, \
         patch('services.agent_run_service.AIService') as mock_ai, \
         patch('services.agent_run_service.VotingService') as mock_voting, \
         patch('services.agent_run_service.SafeService') as mock_safe, \
         patch('services.agent_run_service.UserPreferencesService') as mock_prefs:
        
        # Setup mock returns
        mock_snapshot_instance = AsyncMock()
        mock_ai_instance = AsyncMock()
        mock_voting_instance = AsyncMock()
        mock_safe_instance = AsyncMock()
        mock_prefs_instance = AsyncMock()
        
        mock_snapshot.return_value = mock_snapshot_instance
        mock_ai.return_value = mock_ai_instance
        mock_voting.return_value = mock_voting_instance
        mock_safe.return_value = mock_safe_instance
        mock_prefs.return_value = mock_prefs_instance
        
        yield {
            'snapshot': mock_snapshot_instance,
            'ai': mock_ai_instance,
            'voting': mock_voting_instance,
            'safe': mock_safe_instance,
            'prefs': mock_prefs_instance
        }


@pytest.fixture
def sample_vote_decision():
    """Create a sample vote decision for testing."""
    from models import VoteType, RiskLevel
    
    return VoteDecision(
        proposal_id="0x123",
        vote=VoteType.FOR,
        confidence=0.9,
        reasoning="Test reasoning",
        risk_assessment=RiskLevel.LOW,
        strategy_used=VotingStrategy.BALANCED,
        space_id="test.eth"
    )


@pytest.fixture
def sample_preferences():
    """Create sample user preferences."""
    return UserPreferences(
        strategy=VotingStrategy.BALANCED,
        voter_address="0x742d35Cc6634C0532925a3b844Bc9e7595f8eA9e",
        priorities=["security", "efficiency"],
        excluded_spaces=[],
        min_proposal_age_hours=1,
        delegate_address="0xdelegate"
    )


def create_service_with_mocks(mock_services, state_manager=None):
    """Helper function to create AgentRunService with all necessary mocks."""
    service = AgentRunService(state_manager=state_manager)
    
    # Replace actual services with mocks
    service.voting_service = mock_services['voting']
    service.safe_service = mock_services['safe']
    service.snapshot_service = mock_services['snapshot']
    service.ai_service = mock_services['ai']
    service.user_preferences_service = mock_services['prefs']
    
    # Mock the voting service account
    mock_account = MagicMock()
    mock_account.address = '0xvoter123'
    mock_services['voting'].account = mock_account
    
    # Mock pearl logger but allow info logging for debugging
    service.pearl_logger = MagicMock()
    service.pearl_logger.info.side_effect = lambda msg: print(f"PEARL_LOG: {msg}")
    service.pearl_logger.error.side_effect = lambda msg: print(f"PEARL_ERROR: {msg}")
    
    # Mock state tracker to avoid transition errors
    service.state_tracker = MagicMock()
    service.state_tracker.current_state = 'IDLE'
    
    return service


@pytest.mark.asyncio
async def test_attestation_queued_after_successful_vote(mock_services, sample_vote_decision, sample_preferences):
    """
    Test that an EAS attestation is queued after a successful vote.
    
    This test verifies that:
    1. After a vote is successfully submitted to Snapshot
    2. An attestation is created and added to the pending queue
    3. The attestation contains correct vote data
    """
    # Setup
    # Create a mock state manager
    mock_state_manager = MagicMock()
    checkpoint_data = {}
    
    async def mock_save_checkpoint(key, data):
        checkpoint_data[key] = data
    
    async def mock_load_checkpoint(key):
        return checkpoint_data.get(key)
    
    mock_state_manager.save_checkpoint = AsyncMock(side_effect=mock_save_checkpoint)
    mock_state_manager.load_checkpoint = AsyncMock(side_effect=mock_load_checkpoint)
    
    # Create service with mocks
    service = create_service_with_mocks(mock_services, state_manager=mock_state_manager)
    mock_services['prefs'].load_preferences.return_value = sample_preferences
    mock_services['voting'].vote_on_proposal.return_value = {"success": True, "tx_hash": "0xabc123"}
    
    # Execute
    # Note: _execute_votes takes (decisions, space_id, dry_run, run_id)
    service.run_id = "test_run_123"  # Add run_id attribute
    await service._execute_votes([sample_vote_decision], "test.eth", False, "test_run_123")
    
    # Assert
    # 1. Vote was submitted
    mock_services['voting'].vote_on_proposal.assert_called_once()
    
    # 2. Checkpoint was saved with pending attestations
    saved_checkpoint = await mock_state_manager.load_checkpoint(f"run_test_run_123")
    assert saved_checkpoint is not None, f"No checkpoint found. Available keys: {list(checkpoint_data.keys())}"
    assert 'pending_attestations' in saved_checkpoint
    assert len(saved_checkpoint['pending_attestations']) == 1
    
    # 3. Attestation data is correct
    attestation = saved_checkpoint['pending_attestations'][0]
    assert attestation['proposal_id'] == sample_vote_decision.proposal_id
    assert attestation['vote_choice'] == 1  # FOR maps to 1 in Snapshot
    assert attestation['voter_address'] == '0xvoter123'
    assert attestation['delegate_address'] == '0xvoter123'  # Same as voter_address


@pytest.mark.asyncio
async def test_attestation_failure_does_not_block_voting(mock_services, sample_vote_decision, sample_preferences):
    """
    Test that attestation failures don't block the voting flow.
    
    This test ensures that:
    1. If attestation queueing fails, the vote is still marked as successful
    2. The error is logged but doesn't propagate
    3. The agent run continues normally
    """
    # Setup
    # Create a mock state manager that fails on save
    mock_state_manager = MagicMock()
    mock_state_manager.save_checkpoint = AsyncMock(side_effect=Exception("Storage error"))
    mock_state_manager.load_checkpoint = AsyncMock(return_value=None)
    
    service = create_service_with_mocks(mock_services, state_manager=mock_state_manager)
    mock_services['prefs'].load_preferences.return_value = sample_preferences
    mock_services['voting'].vote_on_proposal.return_value = {"success": True, "tx_hash": "0xabc123"}
    
    # Execute
    executed_decisions = await service._execute_votes([sample_vote_decision], "test.eth", False, "test_run_123")
    
    # Assert
    # Vote was still successful despite attestation queue failure
    assert len(executed_decisions) == 1
    assert executed_decisions[0].proposal_id == sample_vote_decision.proposal_id
    mock_services['voting'].vote_on_proposal.assert_called_once()


@pytest.mark.asyncio
async def test_pending_attestations_processed_on_startup(mock_services, sample_preferences):
    """
    Test that pending attestations from previous runs are processed.
    
    This verifies that:
    1. On agent startup, pending attestations are loaded
    2. The safe service is called to create each attestation
    3. Successfully processed attestations are removed from the queue
    """
    # Setup
    # Create a mock state manager with previous checkpoint
    mock_state_manager = MagicMock()
    
    # Simulate a previous checkpoint with pending attestations
    previous_checkpoint = {
        'space_id': 'test.eth',
        'pending_attestations': [
            {
                'proposal_id': '0x123',
                'vote_choice': 1,
                'voter_address': '0x742d35Cc6634C0532925a3b844Bc9e7595f8eA9e',
                'delegate_address': '0xdelegate',
                'reasoning': 'Test reasoning',
                'vote_tx_hash': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'retry_count': 0
            }
        ]
    }
    
    async def mock_load_checkpoint(key):
        if key == 'agent_checkpoint_test.eth':
            return previous_checkpoint
        return None
    
    mock_state_manager.load_checkpoint = AsyncMock(side_effect=mock_load_checkpoint)
    mock_state_manager.save_checkpoint = AsyncMock()
    
    service = create_service_with_mocks(mock_services, state_manager=mock_state_manager)
    mock_services['prefs'].load_preferences.return_value = sample_preferences
    mock_services['safe'].create_eas_attestation.return_value = {
        'tx_hash': '0xattestation123',
        'attestation_uid': 'uid123'
    }
    
    # Mock snapshot service to return empty proposals (no new work)
    mock_services['snapshot'].get_proposals.return_value = []
    
    # Execute
    from models import AgentRunRequest
    request = AgentRunRequest(space_id='test.eth', dry_run=False)
    result = await service.execute_agent_run(request)
    
    # Assert
    # 1. Safe service was called to create attestation
    mock_services['safe'].create_eas_attestation.assert_called_once()
    call_args = mock_services['safe'].create_eas_attestation.call_args[0][0]
    assert isinstance(call_args, EASAttestationData)
    assert call_args.proposal_id == '0x123'
    
    # 2. Checkpoint was updated to remove processed attestation
    final_checkpoint = mock_state_manager.save_checkpoint.call_args_list[-1][0][1]
    assert 'pending_attestations' in final_checkpoint
    assert len(final_checkpoint['pending_attestations']) == 0


@pytest.mark.asyncio
async def test_failed_attestations_remain_in_queue(mock_services, sample_preferences):
    """
    Test that failed attestations remain in the queue for retry.
    
    Ensures that:
    1. When attestation creation fails, it stays in the queue
    2. The failure is logged but doesn't crash the agent
    3. Other attestations continue to be processed
    """
    # Setup
    # Create a mock state manager with previous checkpoint
    mock_state_manager = MagicMock()
    
    # Two pending attestations
    previous_checkpoint = {
        'space_id': 'test.eth',
        'pending_attestations': [
            {
                'proposal_id': '0x123',
                'vote_choice': 1,
                'voter_address': '0x742d35Cc6634C0532925a3b844Bc9e7595f8eA9e',
                'delegate_address': '0xdelegate',
                'reasoning': 'Test reasoning 1',
                'vote_tx_hash': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'retry_count': 0
            },
            {
                'proposal_id': '0x456',
                'vote_choice': 2,
                'voter_address': '0x742d35Cc6634C0532925a3b844Bc9e7595f8eA9e',
                'delegate_address': '0xdelegate',
                'reasoning': 'Test reasoning 2',
                'vote_tx_hash': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'retry_count': 0
            }
        ]
    }
    
    async def mock_load_checkpoint(key):
        if key == 'agent_checkpoint_test.eth':
            return previous_checkpoint
        return None
    
    mock_state_manager.load_checkpoint = AsyncMock(side_effect=mock_load_checkpoint)
    mock_state_manager.save_checkpoint = AsyncMock()
    
    service = create_service_with_mocks(mock_services, state_manager=mock_state_manager)
    mock_services['prefs'].load_preferences.return_value = sample_preferences
    
    # First attestation fails, second succeeds
    mock_services['safe'].create_eas_attestation.side_effect = [
        Exception("Network error"),
        {'tx_hash': '0xattestation456', 'attestation_uid': 'uid456'}
    ]
    
    mock_services['snapshot'].get_proposals.return_value = []
    
    # Execute
    from models import AgentRunRequest
    request = AgentRunRequest(space_id='test.eth', dry_run=False)
    result = await service.execute_agent_run(request)
    
    # Assert
    # 1. Both attestations were attempted
    assert mock_services['safe'].create_eas_attestation.call_count == 2
    
    # 2. Failed attestation remains in queue with incremented retry count
    final_checkpoint = mock_state_manager.save_checkpoint.call_args_list[-1][0][1]
    assert len(final_checkpoint['pending_attestations']) == 1
    assert final_checkpoint['pending_attestations'][0]['proposal_id'] == '0x123'
    assert final_checkpoint['pending_attestations'][0]['retry_count'] == 1


@pytest.mark.asyncio
async def test_attestation_max_retries_honored(mock_services, sample_preferences):
    """
    Test that attestations are dropped after max retries.
    
    Verifies that:
    1. Attestations with retry_count >= MAX_ATTESTATION_RETRIES are skipped
    2. A warning is logged for dropped attestations
    3. The attestation is removed from the queue
    """
    # Setup
    # Create a mock state manager with previous checkpoint
    mock_state_manager = MagicMock()
    
    # Attestation that has already been retried max times
    previous_checkpoint = {
        'space_id': 'test.eth',
        'pending_attestations': [
            {
                'proposal_id': '0x123',
                'vote_choice': 1,
                'voter_address': '0x742d35Cc6634C0532925a3b844Bc9e7595f8eA9e',
                'delegate_address': '0xdelegate',
                'reasoning': 'Test reasoning',
                'vote_tx_hash': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'retry_count': 3  # Assuming MAX_ATTESTATION_RETRIES = 3
            }
        ]
    }
    
    async def mock_load_checkpoint(key):
        if key == 'agent_checkpoint_test.eth':
            return previous_checkpoint
        return None
    
    mock_state_manager.load_checkpoint = AsyncMock(side_effect=mock_load_checkpoint)
    mock_state_manager.save_checkpoint = AsyncMock()
    
    service = create_service_with_mocks(mock_services, state_manager=mock_state_manager)
    mock_services['prefs'].load_preferences.return_value = sample_preferences
    mock_services['snapshot'].get_proposals.return_value = []
    
    # Execute
    with patch.object(service.pearl_logger, 'warning') as mock_log_warning:
        from models import AgentRunRequest
        request = AgentRunRequest(space_id='test.eth', dry_run=False)
        result = await service.execute_agent_run(request)
    
    # Assert
    # 1. Safe service was NOT called (attestation skipped)
    mock_services['safe'].create_eas_attestation.assert_not_called()
    
    # 2. Warning was logged
    mock_log_warning.assert_called()
    warning_msg = mock_log_warning.call_args[0][0]
    assert "max retries" in warning_msg.lower()
    
    # 3. Attestation removed from queue
    final_checkpoint = mock_state_manager.save_checkpoint.call_args_list[-1][0][1]
    assert len(final_checkpoint['pending_attestations']) == 0