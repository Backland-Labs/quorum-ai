"""
Test suite for AgentRunService status-related methods.

This test suite validates the service methods that support the status endpoint.
Following TDD, these tests define the expected behavior before implementation.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
import os
import json
from services.agent_run_service import AgentRunService
from services.state_transition_tracker import AgentState
from services.state_manager import StateManager


class TestAgentRunServiceStatus:
    """Test cases for AgentRunService status methods."""

    @pytest.fixture
    async def service(self):
        """Create AgentRunService instance with mocked dependencies."""
        mock_state_manager = Mock(spec=StateManager)
        mock_state_manager.load_state = AsyncMock(return_value=None)
        mock_state_manager.save_state = AsyncMock()
        mock_state_manager.store_path = "/tmp/test_store"
        
        service = AgentRunService(state_manager=mock_state_manager)
        await service.initialize()
        return service

    @pytest.mark.asyncio
    async def test_get_latest_checkpoint_returns_most_recent(self, service):
        """
        Verify that get_latest_checkpoint returns the most recent checkpoint.
        
        Why this test is important:
        - Ensures the service correctly identifies the latest run across all spaces
        - Validates timestamp comparison logic works correctly
        - Confirms the method handles multiple checkpoint files properly
        """
        # Mock multiple checkpoint files
        checkpoint1 = {
            "space_id": "gitcoindao.eth",
            "timestamp": "2024-03-15T10:00:00Z",
            "proposals_analyzed": 5
        }
        checkpoint2 = {
            "space_id": "arbitrum.eth",
            "timestamp": "2024-03-15T11:00:00Z",  # More recent
            "proposals_analyzed": 3
        }
        
        # Mock glob to return multiple checkpoint files
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = [
                "/tmp/test_store/agent_checkpoint_gitcoindao.eth.json",
                "/tmp/test_store/agent_checkpoint_arbitrum.eth.json"
            ]
            
            # Mock loading each checkpoint
            service.state_manager.load_state = AsyncMock(
                side_effect=[checkpoint1, checkpoint2]
            )
            
            result = await service.get_latest_checkpoint()
            
            assert result == checkpoint2  # Should return the more recent one
            assert result["space_id"] == "arbitrum.eth"

    @pytest.mark.asyncio
    async def test_get_latest_checkpoint_returns_none_when_no_checkpoints(self, service):
        """
        Verify that get_latest_checkpoint returns None when no checkpoints exist.
        
        Why this test is important:
        - Validates behavior for fresh installations
        - Ensures the method doesn't crash when no data exists
        - Confirms proper None handling for the status endpoint
        """
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = []  # No checkpoint files
            
            result = await service.get_latest_checkpoint()
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_current_state_returns_tracker_state(self, service):
        """
        Verify that get_current_state returns the state from StateTransitionTracker.
        
        Why this test is important:
        - Ensures proper integration with existing state tracking
        - Validates that the method returns valid state values
        - Confirms the state tracker is properly initialized
        """
        # The state tracker should be initialized
        assert hasattr(service, 'state_tracker')
        
        # Get current state
        state = service.get_current_state()
        
        # Should return a valid AgentState value
        assert state in [
            AgentState.IDLE.value,
            AgentState.STARTING.value,
            AgentState.LOADING_PREFERENCES.value,
            AgentState.FETCHING_PROPOSALS.value,
            AgentState.FILTERING_PROPOSALS.value,
            AgentState.ANALYZING_PROPOSAL.value,
            AgentState.DECIDING_VOTE.value,
            AgentState.SUBMITTING_VOTE.value,
            AgentState.COMPLETED.value,
            AgentState.ERROR.value,
            AgentState.SHUTTING_DOWN.value
        ]

    @pytest.mark.asyncio
    async def test_is_agent_active_returns_true_during_run(self, service):
        """
        Verify that is_agent_active correctly identifies active runs.
        
        Why this test is important:
        - Ensures the UI can disable actions during active runs
        - Validates the method checks both _active_run flag and state
        - Confirms proper integration with healthcheck logic
        """
        # Simulate an active run
        service._active_run = True
        service.state_tracker.current_state = AgentState.FETCHING_PROPOSALS
        
        result = service.is_agent_active()
        
        assert result is True

    @pytest.mark.asyncio
    async def test_is_agent_active_returns_false_when_idle(self, service):
        """
        Verify that is_agent_active returns false when agent is idle.
        
        Why this test is important:
        - Ensures the UI enables actions when agent is not running
        - Validates the method correctly identifies idle state
        - Confirms both conditions must be false for inactive status
        """
        # Simulate idle state
        service._active_run = False
        service.state_tracker.current_state = AgentState.IDLE
        
        result = service.is_agent_active()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_all_checkpoint_data_aggregates_correctly(self, service):
        """
        Verify that get_all_checkpoint_data aggregates data from all checkpoints.
        
        Why this test is important:
        - Essential for the decisions and statistics endpoints
        - Validates proper file scanning and loading
        - Ensures all checkpoint data is included in aggregation
        """
        checkpoint1 = {
            "space_id": "gitcoindao.eth",
            "timestamp": "2024-03-15T10:00:00Z",
            "votes_cast": [
                {"proposal_id": "0x123", "vote": "FOR", "confidence": 0.9}
            ]
        }
        checkpoint2 = {
            "space_id": "arbitrum.eth", 
            "timestamp": "2024-03-15T11:00:00Z",
            "votes_cast": [
                {"proposal_id": "0x456", "vote": "AGAINST", "confidence": 0.8}
            ]
        }
        
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = [
                "/tmp/test_store/agent_checkpoint_gitcoindao.eth.json",
                "/tmp/test_store/agent_checkpoint_arbitrum.eth.json"
            ]
            
            service.state_manager.load_state = AsyncMock(
                side_effect=[checkpoint1, checkpoint2]
            )
            
            result = await service.get_all_checkpoint_data()
            
            assert len(result) == 2
            assert result[0] == checkpoint1
            assert result[1] == checkpoint2

    @pytest.mark.asyncio
    async def test_get_latest_checkpoint_handles_corrupted_files(self, service):
        """
        Verify that get_latest_checkpoint handles corrupted checkpoint files gracefully.
        
        Why this test is important:
        - Ensures the service remains resilient to data corruption
        - Validates error handling doesn't crash the entire service
        - Confirms corrupted files are skipped appropriately
        """
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = [
                "/tmp/test_store/agent_checkpoint_corrupted.json",
                "/tmp/test_store/agent_checkpoint_valid.json"
            ]
            
            valid_checkpoint = {
                "space_id": "valid.eth",
                "timestamp": "2024-03-15T10:00:00Z"
            }
            
            # First load returns None (corrupted), second returns valid
            service.state_manager.load_state = AsyncMock(
                side_effect=[None, valid_checkpoint]
            )
            
            result = await service.get_latest_checkpoint()
            
            assert result == valid_checkpoint

    @pytest.mark.asyncio  
    async def test_checkpoint_timestamp_parsing(self, service):
        """
        Verify that checkpoint timestamps are correctly parsed and compared.
        
        Why this test is important:
        - Ensures consistent timestamp handling across the system
        - Validates ISO format parsing works correctly
        - Confirms timezone handling is proper
        """
        checkpoints = [
            {
                "space_id": "test1.eth",
                "timestamp": "2024-03-15T10:00:00Z"  # UTC
            },
            {
                "space_id": "test2.eth", 
                "timestamp": "2024-03-15T12:00:00+02:00"  # With timezone
            },
            {
                "space_id": "test3.eth",
                "timestamp": "2024-03-15T11:30:00Z"  # Latest in UTC
            }
        ]
        
        with patch('glob.glob') as mock_glob:
            mock_glob.return_value = [
                f"/tmp/test_store/agent_checkpoint_{cp['space_id']}.json"
                for cp in checkpoints
            ]
            
            service.state_manager.load_state = AsyncMock(
                side_effect=checkpoints
            )
            
            result = await service.get_latest_checkpoint()
            
            # Should return test3.eth as it's 11:30 UTC (latest)
            assert result["space_id"] == "test3.eth"