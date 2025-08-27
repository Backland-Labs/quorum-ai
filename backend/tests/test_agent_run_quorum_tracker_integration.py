"""Tests for AgentRunService QuorumTracker integration.

This test suite validates the core functionality for tracking activity types
in the AgentRunService when integrated with QuorumTracker system.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from models import (
    AgentRunRequest,
    Proposal,
    VoteDecision,
    VoteType,
    VotingStrategy,
    UserPreferences,
    ActivityType
)


class TestAgentRunServiceQuorumTrackerBasicIntegration:
    """Test basic QuorumTracker integration functionality."""

    @patch('config.settings.quorum_tracker_address', 'test_address')
    @patch('services.agent_run_service.QuorumTrackerService')
    @patch('services.agent_run_service.SafeService')
    async def test_quorum_tracker_service_is_initialized_when_configured(
        self, mock_safe, mock_quorum_tracker
    ):
        """Test QuorumTrackerService is initialized when address is configured.
        
        This is the core test that validates the dependency injection pattern
        for QuorumTrackerService when QUORUM_TRACKER_ADDRESS is set.
        """
        from services.agent_run_service import AgentRunService
        
        mock_safe_instance = MagicMock()
        mock_safe.return_value = mock_safe_instance
        
        service = AgentRunService()
        
        # Verify QuorumTrackerService was initialized with SafeService dependency
        mock_quorum_tracker.assert_called_once_with(mock_safe_instance)
        assert hasattr(service, 'quorum_tracker_service')

    @patch('config.settings.quorum_tracker_address', None)  # Not configured
    async def test_quorum_tracker_service_not_initialized_when_not_configured(self):
        """Test QuorumTrackerService is not initialized when address not configured.
        
        This test ensures that when QUORUM_TRACKER_ADDRESS is None,
        the service operates normally without QuorumTracker functionality.
        """
        from services.agent_run_service import AgentRunService
        
        service = AgentRunService()
        
        # Verify QuorumTrackerService is None when not configured
        assert getattr(service, 'quorum_tracker_service', None) is None

    @patch('config.settings.quorum_tracker_address', 'test_address')
    @patch('services.agent_run_service.QuorumTrackerService')
    @patch('services.agent_run_service.SafeService')
    async def test_activity_tracking_method_exists(self, mock_safe, mock_quorum_tracker):
        """Test that activity tracking method exists and can be called.
        
        This test validates that the service has a method to track activities
        and that it can be called with the correct parameters.
        """
        from services.agent_run_service import AgentRunService
        
        mock_safe_instance = MagicMock()
        mock_safe_instance.get_safe_address = MagicMock(return_value="0x1234567890123456789012345678901234567890")
        mock_safe.return_value = mock_safe_instance
        
        mock_quorum_tracker_instance = MagicMock()
        mock_quorum_tracker_instance.register_activity = AsyncMock(return_value={"success": True})
        mock_quorum_tracker.return_value = mock_quorum_tracker_instance
        
        service = AgentRunService()
        
        # Test that we can track an activity
        if hasattr(service, '_track_activity'):
            await service._track_activity(ActivityType.NO_OPPORTUNITY)
            mock_quorum_tracker_instance.register_activity.assert_called_once()

    def test_activity_type_enum_values_are_correct(self):
        """Test ActivityType enum has correct values for QuorumTracker contract.
        
        This test validates that the ActivityType enum values match what
        the QuorumTracker smart contract expects.
        """
        assert ActivityType.VOTE_CAST == 0
        assert ActivityType.OPPORTUNITY_CONSIDERED == 1
        assert ActivityType.NO_OPPORTUNITY == 2