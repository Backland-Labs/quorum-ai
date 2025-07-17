"""Tests for AgentRunService filtering integration following TDD principles.

This test suite ensures the AgentRunService properly integrates with the
ProposalFilter for intelligent proposal filtering and ranking.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from typing import List, Dict, Any
import time

from models import (
    AgentRunRequest,
    AgentRunResponse,
    Proposal,
    VoteDecision,
    VoteType,
    VotingStrategy,
    RiskLevel,
    UserPreferences,
    ProposalState
)


# Common patch decorator for all tests
def mock_all_services(func):
    """Decorator to mock all services for AgentRunService tests."""
    return patch('services.agent_run_service.ProposalFilter')(
        patch('services.agent_run_service.UserPreferencesService')(
            patch('services.agent_run_service.VotingService')(
                patch('services.agent_run_service.AIService')(
                    patch('services.agent_run_service.SnapshotService')(func)
                )
            )
        )
    )


class TestAgentRunServiceFilteringIntegration:
    """Test AgentRunService integration with ProposalFilter."""

    def _create_test_proposal(self, id: str, author: str, title: str = "Test Proposal",
                            start: int = None, end: int = None, state: str = "active",
                            scores_total: float = 150.0, votes: int = 10) -> Proposal:
        """Helper method to create test proposals."""
        current_time = int(time.time())
        return Proposal(
            id=id,
            title=title,
            choices=["For", "Against"],
            start=start or current_time - 3600,  # 1 hour ago
            end=end or current_time + 3600,  # 1 hour from now
            state=state,
            author=author,
            network="1",
            symbol="TEST",
            scores=[scores_total * 0.7, scores_total * 0.3],
            scores_total=scores_total,
            votes=votes,
            created=current_time - 7200,  # 2 hours ago
            quorum=10.0
        )

    @mock_all_services
    async def test_execute_agent_run_applies_proposal_filtering(self, mock_filter, mock_prefs, mock_voting, mock_ai, mock_snapshot):
        """Test that execute_agent_run applies proposal filtering before making decisions."""
        from services.agent_run_service import AgentRunService
        
        # Mock request
        request = AgentRunRequest(
            space_id="test-space",
            dry_run=False
        )
        
        # Create test proposals (some will be filtered out)
        all_proposals = [
            self._create_test_proposal("prop-1", "0x123"),  # Will be kept
            self._create_test_proposal("prop-2", "0x456"),  # Will be filtered out (blacklisted)
            self._create_test_proposal("prop-3", "0x789"),  # Will be kept
        ]
        
        # Mock filtered proposals (prop-2 removed by blacklist)
        filtered_proposals = [
            all_proposals[0],  # prop-1
            all_proposals[2],  # prop-3
        ]
        
        # Mock ranked proposals (prop-3 ranked higher due to urgency)
        ranked_proposals = [
            all_proposals[2],  # prop-3
            all_proposals[0],  # prop-1
        ]
        
        # Mock user preferences with blacklist
        mock_preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=3,
            blacklisted_proposers=["0x456"]
        )
        
        # Mock vote decisions for filtered proposals
        mock_vote_decisions = [
            VoteDecision(
                proposal_id="prop-3",
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="Test reasoning for prop-3",
                risk_assessment=RiskLevel.LOW,
                strategy_used=VotingStrategy.BALANCED
            ),
            VoteDecision(
                proposal_id="prop-1",
                vote=VoteType.AGAINST,
                confidence=0.9,
                reasoning="Test reasoning for prop-1",
                risk_assessment=RiskLevel.MEDIUM,
                strategy_used=VotingStrategy.BALANCED
            )
        ]
        
        # Setup mocks
        mock_snapshot.return_value.get_proposals = AsyncMock(return_value=all_proposals)
        mock_prefs.return_value.load_preferences = AsyncMock(return_value=mock_preferences)
        
        # Mock ProposalFilter
        mock_filter_instance = MagicMock()
        mock_filter_instance.filter_proposals = MagicMock(return_value=filtered_proposals)
        mock_filter_instance.rank_proposals = MagicMock(return_value=ranked_proposals)
        mock_filter_instance.get_filtering_metrics = MagicMock(return_value={
            "original_count": 3,
            "filtered_count": 2,
            "blacklisted_count": 1,
            "whitelist_filtered_count": 0
        })
        mock_filter.return_value = mock_filter_instance
        
        # Mock AI service to return decisions for filtered proposals
        mock_ai.return_value.decide_vote = AsyncMock(side_effect=mock_vote_decisions)
        
        # Mock voting service
        mock_voting.return_value.vote_on_proposal = AsyncMock(return_value={
            "success": True,
            "transaction_hash": "0xabc123"
        })
        
        service = AgentRunService()
        result = await service.execute_agent_run(request)
        
        # Verify ProposalFilter was initialized with user preferences
        mock_filter.assert_called_once_with(mock_preferences)
        
        # Verify filtering methods were called
        mock_filter_instance.filter_proposals.assert_called_once_with(all_proposals)
        mock_filter_instance.rank_proposals.assert_called_once_with(filtered_proposals)
        
        # Verify AI service was called only for filtered/ranked proposals
        assert mock_ai.return_value.decide_vote.call_count == 2
        # Check that it was called with the ranked proposals
        call_args = mock_ai.return_value.decide_vote.call_args_list
        assert call_args[0][1]['proposal'].id == "prop-3"  # First ranked proposal
        assert call_args[1][1]['proposal'].id == "prop-1"  # Second ranked proposal
        
        # Verify result includes filtered proposals
        assert isinstance(result, AgentRunResponse)
        assert result.space_id == "test-space"
        assert result.proposals_analyzed == 2  # Only filtered proposals
        assert len(result.votes_cast) == 2
        assert result.votes_cast[0].proposal_id == "prop-3"
        assert result.votes_cast[1].proposal_id == "prop-1"
        assert result.user_preferences_applied is True
        assert result.execution_time >= 0.0
        assert result.errors == []

    @mock_all_services
    async def test_execute_agent_run_handles_empty_filtered_proposals(self, mock_filter, mock_prefs, mock_voting, mock_ai, mock_snapshot):
        """Test that execute_agent_run handles empty filtered proposals list."""
        from services.agent_run_service import AgentRunService
        
        # Mock request
        request = AgentRunRequest(
            space_id="test-space",
            dry_run=False
        )
        
        # Create test proposals (all will be filtered out)
        all_proposals = [
            self._create_test_proposal("prop-1", "0x123"),
            self._create_test_proposal("prop-2", "0x456"),
        ]
        
        # Mock user preferences that filter out all proposals
        mock_preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=3,
            blacklisted_proposers=["0x123", "0x456"]  # All authors blacklisted
        )
        
        # Setup mocks
        mock_snapshot.return_value.get_proposals = AsyncMock(return_value=all_proposals)
        mock_prefs.return_value.load_preferences = AsyncMock(return_value=mock_preferences)
        
        # Mock ProposalFilter to return empty lists
        mock_filter_instance = MagicMock()
        mock_filter_instance.filter_proposals = MagicMock(return_value=[])
        mock_filter_instance.rank_proposals = MagicMock(return_value=[])
        mock_filter_instance.get_filtering_metrics = MagicMock(return_value={
            "original_count": 2,
            "filtered_count": 0,
            "blacklisted_count": 2,
            "whitelist_filtered_count": 0
        })
        mock_filter.return_value = mock_filter_instance
        
        service = AgentRunService()
        result = await service.execute_agent_run(request)
        
        # Verify filtering was applied
        mock_filter_instance.filter_proposals.assert_called_once_with(all_proposals)
        mock_filter_instance.rank_proposals.assert_called_once_with([])
        
        # Verify AI and voting services were not called
        mock_ai.return_value.decide_vote.assert_not_called()
        mock_voting.return_value.vote_on_proposal.assert_not_called()
        
        # Verify result reflects no proposals processed
        assert isinstance(result, AgentRunResponse)
        assert result.space_id == "test-space"
        assert result.proposals_analyzed == 0
        assert len(result.votes_cast) == 0
        assert result.user_preferences_applied is True
        assert result.execution_time >= 0.0
        assert result.errors == []

    @mock_all_services
    async def test_execute_agent_run_respects_max_proposals_per_run(self, mock_filter, mock_prefs, mock_voting, mock_ai, mock_snapshot):
        """Test that execute_agent_run respects max_proposals_per_run setting."""
        from services.agent_run_service import AgentRunService
        
        # Mock request
        request = AgentRunRequest(
            space_id="test-space",
            dry_run=False
        )
        
        # Create more proposals than the limit
        all_proposals = [
            self._create_test_proposal("prop-1", "0x123"),
            self._create_test_proposal("prop-2", "0x456"),
            self._create_test_proposal("prop-3", "0x789"),
            self._create_test_proposal("prop-4", "0xabc"),
            self._create_test_proposal("prop-5", "0xdef"),
        ]
        
        # Mock filtered and ranked proposals (all pass filtering)
        filtered_proposals = all_proposals
        ranked_proposals = all_proposals  # Keep same order for simplicity
        
        # Mock user preferences with limit of 3
        mock_preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=3,  # Limit to 3 proposals
            blacklisted_proposers=[]
        )
        
        # Mock vote decisions for first 3 proposals only
        mock_vote_decisions = [
            VoteDecision(
                proposal_id=f"prop-{i}",
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning=f"Test reasoning for prop-{i}",
                risk_assessment=RiskLevel.LOW,
                strategy_used=VotingStrategy.BALANCED
            ) for i in range(1, 4)  # Only first 3 proposals
        ]
        
        # Setup mocks
        mock_snapshot.return_value.get_proposals = AsyncMock(return_value=all_proposals)
        mock_prefs.return_value.load_preferences = AsyncMock(return_value=mock_preferences)
        
        # Mock ProposalFilter
        mock_filter_instance = MagicMock()
        mock_filter_instance.filter_proposals = MagicMock(return_value=filtered_proposals)
        mock_filter_instance.rank_proposals = MagicMock(return_value=ranked_proposals)
        mock_filter_instance.get_filtering_metrics = MagicMock(return_value={
            "original_count": 5,
            "filtered_count": 5,
            "blacklisted_count": 0,
            "whitelist_filtered_count": 0
        })
        mock_filter.return_value = mock_filter_instance
        
        # Mock AI service to return decisions for first 3 proposals
        mock_ai.return_value.decide_vote = AsyncMock(side_effect=mock_vote_decisions)
        
        # Mock voting service
        mock_voting.return_value.vote_on_proposal = AsyncMock(return_value={
            "success": True,
            "transaction_hash": "0xabc123"
        })
        
        service = AgentRunService()
        result = await service.execute_agent_run(request)
        
        # Verify filtering was applied to all proposals
        mock_filter_instance.filter_proposals.assert_called_once_with(all_proposals)
        mock_filter_instance.rank_proposals.assert_called_once_with(filtered_proposals)
        
        # Verify AI service was called only for first 3 proposals (respecting limit)
        assert mock_ai.return_value.decide_vote.call_count == 3
        
        # Verify result respects the limit
        assert isinstance(result, AgentRunResponse)
        assert result.space_id == "test-space"
        assert result.proposals_analyzed == 3  # Limited to 3
        assert len(result.votes_cast) == 3
        assert result.user_preferences_applied is True
        assert result.execution_time >= 0.0
        assert result.errors == []

    @mock_all_services
    async def test_execute_agent_run_includes_filtering_metrics_in_response(self, mock_filter, mock_prefs, mock_voting, mock_ai, mock_snapshot):
        """Test that execute_agent_run includes filtering metrics in response."""
        from services.agent_run_service import AgentRunService
        
        # Mock request
        request = AgentRunRequest(
            space_id="test-space",
            dry_run=False
        )
        
        # Create test proposals
        all_proposals = [
            self._create_test_proposal("prop-1", "0x123"),  # Will be kept
            self._create_test_proposal("prop-2", "0x456"),  # Will be filtered out
        ]
        
        # Mock filtered proposals
        filtered_proposals = [all_proposals[0]]
        ranked_proposals = [all_proposals[0]]
        
        # Mock user preferences
        mock_preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=3,
            blacklisted_proposers=["0x456"]
        )
        
        # Mock vote decision
        mock_vote_decision = VoteDecision(
            proposal_id="prop-1",
            vote=VoteType.FOR,
            confidence=0.8,
            reasoning="Test reasoning",
            risk_assessment=RiskLevel.LOW,
            strategy_used=VotingStrategy.BALANCED
        )
        
        # Mock filtering metrics
        mock_filtering_metrics = {
            "original_count": 2,
            "filtered_count": 1,
            "blacklisted_count": 1,
            "whitelist_filtered_count": 0,
            "filter_efficiency": 0.5,
            "blacklisted_proposers": 1,
            "whitelisted_proposers": 0,
            "has_whitelist": False,
            "has_blacklist": True
        }
        
        # Setup mocks
        mock_snapshot.return_value.get_proposals = AsyncMock(return_value=all_proposals)
        mock_prefs.return_value.load_preferences = AsyncMock(return_value=mock_preferences)
        
        # Mock ProposalFilter
        mock_filter_instance = MagicMock()
        mock_filter_instance.filter_proposals = MagicMock(return_value=filtered_proposals)
        mock_filter_instance.rank_proposals = MagicMock(return_value=ranked_proposals)
        mock_filter_instance.get_filtering_metrics = MagicMock(return_value=mock_filtering_metrics)
        mock_filter.return_value = mock_filter_instance
        
        # Mock AI service
        mock_ai.return_value.decide_vote = AsyncMock(return_value=mock_vote_decision)
        
        # Mock voting service
        mock_voting.return_value.vote_on_proposal = AsyncMock(return_value={
            "success": True,
            "transaction_hash": "0xabc123"
        })
        
        service = AgentRunService()
        result = await service.execute_agent_run(request)
        
        # Verify filtering metrics were requested
        mock_filter_instance.get_filtering_metrics.assert_called_once_with(all_proposals, filtered_proposals)
        
        # Verify result includes filtering metrics (if implemented in the response)
        assert isinstance(result, AgentRunResponse)
        assert result.space_id == "test-space"
        assert result.proposals_analyzed == 1
        assert len(result.votes_cast) == 1
        assert result.user_preferences_applied is True
        assert result.execution_time >= 0.0
        assert result.errors == []

    @mock_all_services
    async def test_execute_agent_run_handles_filtering_errors_gracefully(self, mock_filter, mock_prefs, mock_voting, mock_ai, mock_snapshot):
        """Test that execute_agent_run handles filtering errors gracefully."""
        from services.agent_run_service import AgentRunService
        
        # Mock request
        request = AgentRunRequest(
            space_id="test-space",
            dry_run=False
        )
        
        # Create test proposals
        all_proposals = [
            self._create_test_proposal("prop-1", "0x123"),
            self._create_test_proposal("prop-2", "0x456"),
        ]
        
        # Mock user preferences
        mock_preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=3
        )
        
        # Setup mocks
        mock_snapshot.return_value.get_proposals = AsyncMock(return_value=all_proposals)
        mock_prefs.return_value.load_preferences = AsyncMock(return_value=mock_preferences)
        
        # Mock ProposalFilter to raise an error
        mock_filter_instance = MagicMock()
        mock_filter_instance.filter_proposals = MagicMock(side_effect=Exception("Filtering error"))
        mock_filter.return_value = mock_filter_instance
        
        service = AgentRunService()
        result = await service.execute_agent_run(request)
        
        # Verify error was handled gracefully
        assert isinstance(result, AgentRunResponse)
        assert result.space_id == "test-space"
        assert result.proposals_analyzed == 0  # No proposals processed due to error
        assert len(result.votes_cast) == 0
        assert result.user_preferences_applied is True
        assert result.execution_time >= 0.0
        assert len(result.errors) > 0  # Should contain filtering error
        assert any("Filtering error" in error for error in result.errors)

    @mock_all_services
    async def test_execute_agent_run_fallback_to_unfiltered_on_filter_error(self, mock_filter, mock_prefs, mock_voting, mock_ai, mock_snapshot):
        """Test that execute_agent_run falls back to unfiltered proposals on filter error."""
        from services.agent_run_service import AgentRunService
        
        # Mock request
        request = AgentRunRequest(
            space_id="test-space",
            dry_run=False
        )
        
        # Create test proposals
        all_proposals = [
            self._create_test_proposal("prop-1", "0x123"),
        ]
        
        # Mock user preferences
        mock_preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=3
        )
        
        # Mock vote decision
        mock_vote_decision = VoteDecision(
            proposal_id="prop-1",
            vote=VoteType.FOR,
            confidence=0.8,
            reasoning="Test reasoning",
            risk_assessment=RiskLevel.LOW,
            strategy_used=VotingStrategy.BALANCED
        )
        
        # Setup mocks
        mock_snapshot.return_value.get_proposals = AsyncMock(return_value=all_proposals)
        mock_prefs.return_value.load_preferences = AsyncMock(return_value=mock_preferences)
        
        # Mock ProposalFilter to raise an error on filtering but work on fallback
        mock_filter_instance = MagicMock()
        mock_filter_instance.filter_proposals = MagicMock(side_effect=Exception("Filtering error"))
        mock_filter.return_value = mock_filter_instance
        
        # Mock AI service
        mock_ai.return_value.decide_vote = AsyncMock(return_value=mock_vote_decision)
        
        # Mock voting service
        mock_voting.return_value.vote_on_proposal = AsyncMock(return_value={
            "success": True,
            "transaction_hash": "0xabc123"
        })
        
        service = AgentRunService()
        result = await service.execute_agent_run(request)
        
        # Verify that despite filtering error, execution continued with original proposals
        assert isinstance(result, AgentRunResponse)
        assert result.space_id == "test-space"
        assert result.proposals_analyzed == 1  # Original proposals were processed
        assert len(result.votes_cast) == 1
        assert result.user_preferences_applied is True
        assert result.execution_time >= 0.0
        assert len(result.errors) > 0  # Should contain filtering error
        assert any("Filtering error" in error for error in result.errors)