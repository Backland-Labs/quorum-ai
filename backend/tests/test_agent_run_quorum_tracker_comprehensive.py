"""Comprehensive tests for AgentRunService QuorumTracker integration.

This test suite validates the complete workflow integration with activity tracking.
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


class TestAgentRunServiceQuorumTrackerWorkflow:
    """Test complete workflow with QuorumTracker integration."""

    @patch('config.settings.quorum_tracker_address', 'test_address')
    @patch('services.agent_run_service.QuorumTrackerService')
    @patch('services.agent_run_service.SafeService')
    @patch('services.agent_run_service.UserPreferencesService')
    @patch('services.agent_run_service.SnapshotService')
    async def test_no_opportunity_tracked_when_no_proposals(
        self,
        mock_snapshot,
        mock_prefs,
        mock_safe,
        mock_quorum_tracker
    ):
        """Test NO_OPPORTUNITY is tracked when no proposals are found.
        
        This test validates the complete workflow when SnapshotService
        returns no active proposals for the given space.
        """
        from services.agent_run_service import AgentRunService
        
        # Setup mocks
        mock_safe_instance = MagicMock()
        mock_safe_instance.safe_addresses = {"base": "0x1234567890123456789012345678901234567890"}
        mock_safe.return_value = mock_safe_instance
        
        mock_quorum_tracker_instance = MagicMock()
        mock_quorum_tracker_instance.register_activity = AsyncMock(return_value={"success": True})
        mock_quorum_tracker.return_value = mock_quorum_tracker_instance
        
        mock_prefs_instance = MagicMock()
        mock_prefs_instance.load_preferences = AsyncMock(return_value=UserPreferences())
        mock_prefs.return_value = mock_prefs_instance
        
        mock_snapshot_instance = MagicMock()
        mock_snapshot_instance.get_proposals = AsyncMock(return_value=[])  # No proposals
        mock_snapshot.return_value = mock_snapshot_instance
        
        # Execute test
        service = AgentRunService()
        await service.initialize()
        
        request = AgentRunRequest(space_id="test-space", dry_run=False)
        response = await service.execute_agent_run(request)
        
        # Verify NO_OPPORTUNITY activity was registered
        mock_quorum_tracker_instance.register_activity.assert_called_once_with(
            multisig_address="0x1234567890123456789012345678901234567890",
            activity_type=ActivityType.NO_OPPORTUNITY.value
        )
        
        # Verify response
        assert response.space_id == "test-space"
        assert response.proposals_analyzed == 0
        assert len(response.votes_cast) == 0

    @patch('config.settings.quorum_tracker_address', 'test_address')
    @patch('services.agent_run_service.QuorumTrackerService')
    @patch('services.agent_run_service.SafeService')
    @patch('services.agent_run_service.UserPreferencesService')
    @patch('services.agent_run_service.SnapshotService')
    @patch('services.agent_run_service.AIService')
    async def test_opportunity_considered_tracked_for_low_confidence_decisions(
        self,
        mock_ai,
        mock_snapshot,
        mock_prefs,
        mock_safe,
        mock_quorum_tracker
    ):
        """Test OPPORTUNITY_CONSIDERED is tracked when confidence is below threshold.
        
        This test validates that when AI makes a voting decision but the confidence
        is below the user's threshold, an OPPORTUNITY_CONSIDERED activity is tracked.
        """
        from services.agent_run_service import AgentRunService
        
        # Setup mocks
        mock_safe_instance = MagicMock()
        mock_safe_instance.safe_addresses = {"base": "0x1234567890123456789012345678901234567890"}
        mock_safe.return_value = mock_safe_instance
        
        mock_quorum_tracker_instance = MagicMock()
        mock_quorum_tracker_instance.register_activity = AsyncMock(return_value={"success": True})
        mock_quorum_tracker.return_value = mock_quorum_tracker_instance
        
        # High confidence threshold so decision gets rejected
        mock_prefs_instance = MagicMock()
        mock_prefs_instance.load_preferences = AsyncMock(
            return_value=UserPreferences(confidence_threshold=0.9)
        )
        mock_prefs.return_value = mock_prefs_instance
        
        # Mock proposal
        test_proposal = Proposal(
            id="prop-1",
            title="Test Proposal",
            body="Test proposal body",
            choices=["For", "Against"],
            start=1698768000,
            end=1699372800,
            state="active",
            author="0x1234567890123456789012345678901234567890",  # Valid address
            scores=[100.0, 50.0],
            scores_total=150.0,
            votes=10,
            created=1698681600
        )
        
        mock_snapshot_instance = MagicMock()
        mock_snapshot_instance.get_proposals = AsyncMock(return_value=[test_proposal])
        mock_snapshot.return_value = mock_snapshot_instance
        
        # Mock AI decision with low confidence (below 0.9 threshold)
        low_confidence_decision = VoteDecision(
            proposal_id="prop-1",
            vote=VoteType.FOR,
            confidence=0.5,  # Below 0.9 threshold
            reasoning="Low confidence test decision",
            strategy_used=VotingStrategy.BALANCED
        )
        
        mock_ai_instance = MagicMock()
        mock_ai_instance.decide_vote = AsyncMock(return_value=low_confidence_decision)
        mock_ai.return_value = mock_ai_instance
        
        # Execute test
        service = AgentRunService()
        await service.initialize()
        
        request = AgentRunRequest(space_id="test-space", dry_run=False)
        response = await service.execute_agent_run(request)
        
        # Verify OPPORTUNITY_CONSIDERED activity was registered
        mock_quorum_tracker_instance.register_activity.assert_called_once_with(
            multisig_address="0x1234567890123456789012345678901234567890",
            activity_type=ActivityType.OPPORTUNITY_CONSIDERED.value
        )
        
        # Verify response
        assert response.space_id == "test-space"
        assert response.proposals_analyzed == 1
        assert len(response.votes_cast) == 0  # No votes cast due to low confidence

    @patch('config.settings.quorum_tracker_address', 'test_address')
    @patch('services.agent_run_service.QuorumTrackerService')
    @patch('services.agent_run_service.SafeService')
    @patch('services.agent_run_service.UserPreferencesService')
    @patch('services.agent_run_service.SnapshotService')
    @patch('services.agent_run_service.AIService')
    @patch('services.agent_run_service.VotingService')
    async def test_vote_cast_tracked_for_successful_votes(
        self,
        mock_voting,
        mock_ai,
        mock_snapshot,
        mock_prefs,
        mock_safe,
        mock_quorum_tracker
    ):
        """Test VOTE_CAST is tracked when votes are successfully executed.
        
        This test validates that when a high-confidence decision is made and
        successfully executed as a vote, a VOTE_CAST activity is tracked.
        """
        from services.agent_run_service import AgentRunService
        
        # Setup mocks
        mock_safe_instance = MagicMock()
        mock_safe_instance.safe_addresses = {"base": "0x1234567890123456789012345678901234567890"}
        mock_safe.return_value = mock_safe_instance
        
        mock_quorum_tracker_instance = MagicMock()
        mock_quorum_tracker_instance.register_activity = AsyncMock(return_value={"success": True})
        mock_quorum_tracker.return_value = mock_quorum_tracker_instance
        
        # Low confidence threshold so decision gets accepted
        mock_prefs_instance = MagicMock()
        mock_prefs_instance.load_preferences = AsyncMock(
            return_value=UserPreferences(confidence_threshold=0.5)
        )
        mock_prefs.return_value = mock_prefs_instance
        
        # Mock proposal
        test_proposal = Proposal(
            id="prop-1",
            title="Test Proposal",
            body="Test proposal body",
            choices=["For", "Against"],
            start=1698768000,
            end=1699372800,
            state="active",
            author="0x1234567890123456789012345678901234567890",  # Valid address
            scores=[100.0, 50.0],
            scores_total=150.0,
            votes=10,
            created=1698681600
        )
        
        mock_snapshot_instance = MagicMock()
        mock_snapshot_instance.get_proposals = AsyncMock(return_value=[test_proposal])
        mock_snapshot.return_value = mock_snapshot_instance
        
        # Mock AI decision with high confidence (above 0.5 threshold)
        high_confidence_decision = VoteDecision(
            proposal_id="prop-1",
            vote=VoteType.FOR,
            confidence=0.9,  # Above 0.5 threshold
            reasoning="High confidence test decision",
            strategy_used=VotingStrategy.BALANCED
        )
        
        mock_ai_instance = MagicMock()
        mock_ai_instance.decide_vote = AsyncMock(return_value=high_confidence_decision)
        mock_ai.return_value = mock_ai_instance
        
        # Mock successful vote execution
        mock_voting_instance = MagicMock()
        mock_voting_instance.vote_on_proposal = AsyncMock(
            return_value={"success": True, "tx_hash": "0x123abc"}
        )
        mock_voting.return_value = mock_voting_instance
        
        # Execute test
        service = AgentRunService()
        await service.initialize()
        
        request = AgentRunRequest(space_id="test-space", dry_run=False)
        response = await service.execute_agent_run(request)
        
        # Verify VOTE_CAST activity was registered
        mock_quorum_tracker_instance.register_activity.assert_called_once_with(
            multisig_address="0x1234567890123456789012345678901234567890",
            activity_type=ActivityType.VOTE_CAST.value
        )
        
        # Verify vote was executed
        mock_voting_instance.vote_on_proposal.assert_called_once()
        
        # Verify response
        assert response.space_id == "test-space"
        assert response.proposals_analyzed == 1
        assert len(response.votes_cast) == 1