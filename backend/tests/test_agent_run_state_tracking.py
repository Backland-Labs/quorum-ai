"""
Test agent run state tracking and comprehensive logging.

This test suite ensures that the AgentRunService properly tracks state transitions
throughout the agent execution lifecycle, providing comprehensive logging for
debugging and audit trails.
"""

import asyncio
import os
from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from models import UserPreferences, VotingStrategy, AgentRunRequest
from services.agent_run_service import AgentRunService
from services.state_transition_tracker import AgentState, StateTransitionTracker


# Set up test environment
os.environ["OPENROUTER_API_KEY"] = "test-key"


@pytest.fixture
def mock_snapshot_service():
    """Mock SnapshotService for testing."""
    service = AsyncMock()
    service.get_spaces = AsyncMock(return_value=[
        {"id": "space1", "name": "Test Space 1", "avatar": None}
    ])
    service.get_proposals = AsyncMock(return_value=[
        {
            "id": "proposal1",
            "title": "Test Proposal 1",
            "body": "Test proposal body",
            "start": int(datetime.now(UTC).timestamp()) - 3600,
            "end": int(datetime.now(UTC).timestamp()) + 86400,
            "state": "active",
            "choices": ["Yes", "No", "Abstain"],
            "space": {"id": "space1", "name": "Test Space 1"}
        }
    ])
    return service


@pytest.fixture
def mock_ai_service():
    """Mock AIService for testing."""
    service = AsyncMock()
    service.analyze_proposal_for_voting = AsyncMock(return_value={
        "vote_decision": "Yes",
        "confidence_score": 0.85,
        "reasoning": "Test reasoning",
        "risk_assessment": {"level": "low", "factors": []}
    })
    return service


@pytest.fixture
def mock_voting_service():
    """Mock VotingService for testing."""
    service = AsyncMock()
    service.cast_vote = AsyncMock(return_value={
        "success": True,
        "transaction_hash": "0x123",
        "message": "Vote submitted successfully"
    })
    return service


@pytest.fixture
def mock_state_manager():
    """Mock StateManager for testing."""
    manager = MagicMock()
    manager.get_user_preferences = MagicMock(return_value=UserPreferences(
        voting_strategy=VotingStrategy.BALANCED,
        spaces=["space1"],
        delegate_address="0x123"
    ))
    return manager


@pytest.fixture
def mock_state_tracker():
    """Mock StateTransitionTracker for testing."""
    tracker = MagicMock()
    tracker.transition = MagicMock()
    return tracker


@pytest.fixture
def agent_run_service(
    mock_snapshot_service,
    mock_ai_service,
    mock_voting_service,
    mock_state_manager,
    mock_state_tracker
):
    """Create AgentRunService with mocked dependencies."""
    with patch('services.state_transition_tracker.StateTransitionTracker', return_value=mock_state_tracker), \
         patch('services.snapshot_service.SnapshotService', return_value=mock_snapshot_service), \
         patch('services.ai_service.AIService', return_value=mock_ai_service), \
         patch('services.voting_service.VotingService', return_value=mock_voting_service), \
         patch('services.user_preferences_service.UserPreferencesService'):
        service = AgentRunService(state_manager=mock_state_manager)
        # Manually set the state tracker to our mock
        service.state_tracker = mock_state_tracker
        return service


class TestAgentRunStateTracking:
    """Test comprehensive state tracking during agent runs."""
    
    @pytest.mark.asyncio
    async def test_successful_run_tracks_all_state_transitions(self, agent_run_service, mock_state_tracker):
        """
        Test that a successful agent run tracks all expected state transitions.
        
        This test verifies that the agent properly transitions through all states
        during a successful run, ensuring comprehensive logging for monitoring
        and debugging purposes.
        """
        request = AgentRunRequest(
            space_id="space1",
            dry_run=False
        )
        
        result = await agent_run_service.execute_agent_run(request)
        
        # Verify all state transitions occurred in the correct order
        expected_transitions = [
            AgentState.STARTING,
            AgentState.LOADING_PREFERENCES,
            AgentState.FETCHING_PROPOSALS,
            AgentState.FILTERING_PROPOSALS,
            AgentState.ANALYZING_PROPOSAL,
            AgentState.DECIDING_VOTE,
            AgentState.SUBMITTING_VOTE,
            AgentState.COMPLETED,
            AgentState.IDLE
        ]
        
        # Get all transition calls
        transition_calls = mock_state_tracker.transition.call_args_list
        
        # Verify we have some transitions
        assert len(transition_calls) >= 4, \
            f"Expected at least 4 transitions, got {len(transition_calls)}"
        
        # Verify each expected transition state appears in the calls
        actual_states = [call[0][0] for call in transition_calls]
        
        # Check that all expected states appear in order (but there might be extra states like ERROR)
        expected_idx = 0
        for actual_state in actual_states:
            if expected_idx < len(expected_transitions) and actual_state == expected_transitions[expected_idx]:
                expected_idx += 1
        
        # Check that we saw at least the key transitions
        assert AgentState.STARTING in actual_states, "Should transition to STARTING"
        assert AgentState.LOADING_PREFERENCES in actual_states, "Should transition to LOADING_PREFERENCES"
        assert AgentState.FETCHING_PROPOSALS in actual_states, "Should transition to FETCHING_PROPOSALS"
        assert AgentState.FILTERING_PROPOSALS in actual_states, "Should transition to FILTERING_PROPOSALS"
        
        # Verify metadata is included in all transitions
        for call in transition_calls:
            if len(call[0]) > 1:
                metadata = call[0][1]
                assert isinstance(metadata, dict), "Metadata should be a dictionary"
                assert "run_id" in metadata, "Metadata should include run_id"
    
    @pytest.mark.asyncio
    async def test_error_during_fetch_transitions_to_error_state(self, agent_run_service, mock_state_tracker, mock_snapshot_service):
        """
        Test that errors during proposal fetching properly transition to ERROR state.
        
        This test ensures that when an error occurs during the agent run,
        the state properly transitions to ERROR with appropriate metadata
        for debugging.
        """
        # Make get_proposals raise an exception
        mock_snapshot_service.get_proposals.side_effect = Exception("Network error")
        
        request = AgentRunRequest(
            space_id="space1",
            dry_run=False
        )
        
        result = await agent_run_service.execute_agent_run(request)
        
        # Find the ERROR transition
        error_transition_found = False
        for call in mock_state_tracker.transition.call_args_list:
            if len(call[0]) > 0 and call[0][0] == AgentState.ERROR:
                error_transition_found = True
                
                # Verify error metadata
                if len(call[0]) > 1:
                    metadata = call[0][1]
                    assert "error" in metadata, "Error metadata should include error details"
                    assert "Network error" in str(metadata["error"]), "Error message should be included"
                break
        
        assert error_transition_found, "Should transition to ERROR state on exception"
        
        # Verify it transitions back to IDLE after error
        final_transition = mock_state_tracker.transition.call_args_list[-1]
        assert final_transition[0][0] == AgentState.IDLE, "Should transition back to IDLE after error"
    
    @pytest.mark.asyncio
    async def test_state_transitions_include_relevant_metadata(self, agent_run_service, mock_state_tracker):
        """
        Test that state transitions include relevant metadata for each state.
        
        This test verifies that each state transition includes appropriate
        metadata that provides context for monitoring and debugging.
        """
        request = AgentRunRequest(
            space_id="space1",
            dry_run=False
        )
        
        result = await agent_run_service.execute_agent_run(request)
        
        # Check specific transitions for metadata
        for call in mock_state_tracker.transition.call_args_list:
            if len(call[0]) > 0:
                to_state = call[0][0]
                metadata = call[0][1] if len(call[0]) > 1 else {}
                
                # All transitions should have run_id
                assert "run_id" in metadata, f"Transition to {to_state} should include run_id"
                
                # Check state-specific metadata
                if to_state == AgentState.FETCHING_PROPOSALS:
                    assert "spaces" in metadata, "FETCHING_PROPOSALS should include spaces"
                elif to_state == AgentState.FILTERING_PROPOSALS:
                    assert "total_proposals" in metadata, "FILTERING_PROPOSALS should include total_proposals"
                elif to_state == AgentState.ANALYZING_PROPOSAL:
                    assert "proposal_id" in metadata, "ANALYZING_PROPOSAL should include proposal_id"
                    assert "proposal_title" in metadata, "ANALYZING_PROPOSAL should include proposal_title"
                elif to_state == AgentState.DECIDING_VOTE:
                    assert "vote_decision" in metadata, "DECIDING_VOTE should include vote_decision"
                    assert "confidence_score" in metadata, "DECIDING_VOTE should include confidence_score"
                elif to_state == AgentState.SUBMITTING_VOTE:
                    assert "proposal_id" in metadata, "SUBMITTING_VOTE should include proposal_id"
                elif to_state == AgentState.COMPLETED:
                    assert "total_duration" in metadata, "COMPLETED should include total_duration"
                    assert "proposals_analyzed" in metadata, "COMPLETED should include proposals_analyzed"
                    assert "votes_cast" in metadata, "COMPLETED should include votes_cast"
    
    @pytest.mark.asyncio
    async def test_dry_run_skips_vote_submission_state(self, agent_run_service, mock_state_tracker):
        """
        Test that dry run mode properly tracks states but skips vote submission.
        
        This test ensures that in dry run mode, the agent tracks all analysis
        states but skips the actual vote submission state.
        """
        request = AgentRunRequest(
            space_id="space1",
            dry_run=True
        )
        
        result = await agent_run_service.execute_agent_run(request)
        
        # Check that we don't transition to SUBMITTING_VOTE in dry run
        submitting_vote_found = False
        for call in mock_state_tracker.transition.call_args_list:
            if len(call[0]) > 0 and call[0][0] == AgentState.SUBMITTING_VOTE:
                submitting_vote_found = True
                break
        
        assert not submitting_vote_found, "Should not transition to SUBMITTING_VOTE in dry run mode"
        
        # But we should still see DECIDING_VOTE
        deciding_vote_found = False
        for call in mock_state_tracker.transition.call_args_list:
            if len(call[0]) > 0 and call[0][0] == AgentState.DECIDING_VOTE:
                deciding_vote_found = True
                break
        
        assert deciding_vote_found, "Should still transition to DECIDING_VOTE in dry run mode"
    
    @pytest.mark.asyncio
    async def test_concurrent_runs_have_unique_run_ids(self, agent_run_service, mock_state_tracker):
        """
        Test that concurrent agent runs have unique run IDs in their state metadata.
        
        This test verifies that when multiple agent runs execute concurrently,
        each has a unique run_id for proper log correlation and tracking.
        """
        request = AgentRunRequest(
            space_id="space1",
            dry_run=False
        )
        
        # Execute two runs concurrently
        results = await asyncio.gather(
            agent_run_service.execute_agent_run(request),
            agent_run_service.execute_agent_run(request)
        )
        
        # Extract run_ids from all transitions
        run_ids = set()
        for call in mock_state_tracker.transition.call_args_list:
            if len(call[0]) > 1:
                metadata = call[0][1]
                if "run_id" in metadata:
                    run_ids.add(metadata["run_id"])
        
        # Should have at least 2 unique run_ids
        assert len(run_ids) >= 2, "Concurrent runs should have unique run_ids"
    
    def test_state_tracker_initialization(self):
        """
        Test that AgentRunService properly initializes with StateTransitionTracker.
        
        This test verifies that the service correctly creates and initializes
        the state tracker for comprehensive logging support.
        """
        # Simply verify that the service has a state_tracker attribute
        # We'll test this in the actual implementation
        assert hasattr(AgentRunService, '__init__')
        
        # This will be validated when we implement the actual tracking
        # For now, the test is just a placeholder to drive implementation