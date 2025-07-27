"""Tests for AgentRunService following TDD principles."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
from typing import List, Dict, Any

from models import (
    AgentRunRequest,
    AgentRunResponse, 
    Proposal,
    VoteDecision,
    VoteType,
    VotingStrategy,
    RiskLevel,
    UserPreferences
)


# Common patch decorator for all tests
def mock_all_services(func):
    """Decorator to mock all services for AgentRunService tests."""
    return patch('services.agent_run_service.UserPreferencesService')(
        patch('services.agent_run_service.VotingService')(
            patch('services.agent_run_service.AIService')(
                patch('services.agent_run_service.SnapshotService')(func)
            )
        )
    )


class TestAgentRunServiceInitialization:
    """Test AgentRunService initialization and dependency injection."""

    @mock_all_services
    def test_agent_run_service_initialization(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test AgentRunService initializes with required dependencies."""
        from services.agent_run_service import AgentRunService
        
        service = AgentRunService()
        
        # Runtime assertions for service initialization
        assert service.snapshot_service is not None
        assert service.ai_service is not None
        assert service.voting_service is not None
        assert service.user_preferences_service is not None
        
        # Verify service types
        assert hasattr(service, 'snapshot_service')
        assert hasattr(service, 'ai_service')
        assert hasattr(service, 'voting_service')
        assert hasattr(service, 'user_preferences_service')
        
        # Verify mocked services were instantiated
        mock_snapshot.assert_called_once()
        mock_ai.assert_called_once()
        mock_voting.assert_called_once()
        mock_prefs.assert_called_once()

    @mock_all_services
    def test_agent_run_service_initialization_with_mocks(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test AgentRunService initialization with mocked dependencies."""
        from services.agent_run_service import AgentRunService
        
        service = AgentRunService()
        
        # Verify mocked services were instantiated
        mock_snapshot.assert_called_once()
        mock_ai.assert_called_once()
        mock_voting.assert_called_once()
        mock_prefs.assert_called_once()


class TestAgentRunServiceFetchActiveProposals:
    """Test AgentRunService _fetch_active_proposals method."""

    @mock_all_services
    async def test_fetch_active_proposals_success(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test successful fetching of active proposals."""
        from services.agent_run_service import AgentRunService
        
        # Mock proposals
        mock_proposals = [
            Proposal(
                id="prop-1",
                title="Test Proposal 1",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=1698681600,
                quorum=10.0
            ),
            Proposal(
                id="prop-2",
                title="Test Proposal 2",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x456",
                network="1",
                symbol="TEST",
                scores=[200.0, 25.0],
                scores_total=225.0,
                votes=15,
                created=1698681600,
                quorum=10.0
            )
        ]
        
        mock_snapshot.return_value.get_proposals = AsyncMock(return_value=mock_proposals)
        
        service = AgentRunService()
        result = await service._fetch_active_proposals("test-space", 5)
        
        # Verify the result
        assert len(result) == 2
        assert all(isinstance(p, Proposal) for p in result)
        assert result[0].id == "prop-1"
        assert result[1].id == "prop-2"
        
        # Verify service was called correctly
        mock_snapshot.return_value.get_proposals.assert_called_once_with(
            space_ids=["test-space"], state="active", first=5
        )

    @mock_all_services
    async def test_fetch_active_proposals_empty_result(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test fetching active proposals with empty result."""
        from services.agent_run_service import AgentRunService
        
        mock_snapshot.return_value.get_proposals = AsyncMock(return_value=[])
        
        service = AgentRunService()
        result = await service._fetch_active_proposals("test-space", 5)
        
        assert result == []
        mock_snapshot.return_value.get_proposals.assert_called_once_with(
            space_ids=["test-space"], state="active", first=5
        )

    @mock_all_services
    async def test_fetch_active_proposals_service_error(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test fetching active proposals with service error."""
        from services.agent_run_service import AgentRunService
        
        mock_snapshot.return_value.get_proposals = AsyncMock(side_effect=Exception("Service error"))
        
        service = AgentRunService()
        
        with pytest.raises(Exception, match="Service error"):
            await service._fetch_active_proposals("test-space", 5)

    @mock_all_services
    async def test_fetch_active_proposals_respects_limit(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test fetching active proposals respects limit parameter."""
        from services.agent_run_service import AgentRunService
        
        mock_snapshot.return_value.get_proposals = AsyncMock(return_value=[])
        
        service = AgentRunService()
        await service._fetch_active_proposals("test-space", 3)
        
        mock_snapshot.return_value.get_proposals.assert_called_once_with(
            space_ids=["test-space"], state="active", first=3
        )


class TestAgentRunServiceMakeVotingDecisions:
    """Test AgentRunService _make_voting_decisions method."""

    @mock_all_services
    async def test_make_voting_decisions_success(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test successful voting decisions generation."""
        from services.agent_run_service import AgentRunService
        
        # Mock proposals
        proposals = [
            Proposal(
                id="prop-1",
                title="Test Proposal 1",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=1698681600,
                quorum=10.0
            )
        ]
        
        # Mock user preferences
        preferences = UserPreferences(
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
        
        mock_ai.return_value.decide_vote = AsyncMock(return_value=mock_vote_decision)
        
        service = AgentRunService()
        result = await service._make_voting_decisions(proposals, preferences)
        
        # Verify result
        assert len(result) == 1
        assert isinstance(result[0], VoteDecision)
        assert result[0].proposal_id == "prop-1"
        assert result[0].vote == VoteType.FOR
        assert result[0].confidence == 0.8
        
        # Verify AI service was called correctly
        mock_ai.return_value.decide_vote.assert_called_once_with(
            proposal=proposals[0], strategy=VotingStrategy.BALANCED
        )

    @mock_all_services
    async def test_make_voting_decisions_multiple_proposals(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test voting decisions for multiple proposals."""
        from services.agent_run_service import AgentRunService
        
        # Mock proposals
        proposals = [
            Proposal(
                id="prop-1",
                title="Test Proposal 1",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=1698681600,
                quorum=10.0
            ),
            Proposal(
                id="prop-2",
                title="Test Proposal 2",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x456",
                network="1",
                symbol="TEST",
                scores=[200.0, 25.0],
                scores_total=225.0,
                votes=15,
                created=1698681600,
                quorum=10.0
            )
        ]
        
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.AGGRESSIVE,
            confidence_threshold=0.6
        )
        
        # Mock vote decisions
        mock_vote_decisions = [
            VoteDecision(
                proposal_id="prop-1",
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="Test reasoning 1",
                risk_assessment=RiskLevel.LOW,
                strategy_used=VotingStrategy.AGGRESSIVE
            ),
            VoteDecision(
                proposal_id="prop-2",
                vote=VoteType.AGAINST,
                confidence=0.7,
                reasoning="Test reasoning 2",
                risk_assessment=RiskLevel.HIGH,
                strategy_used=VotingStrategy.AGGRESSIVE
            )
        ]
        
        mock_ai.return_value.decide_vote = AsyncMock(side_effect=mock_vote_decisions)
        
        service = AgentRunService()
        result = await service._make_voting_decisions(proposals, preferences)
        
        # Verify result
        assert len(result) == 2
        assert all(isinstance(d, VoteDecision) for d in result)
        assert result[0].proposal_id == "prop-1"
        assert result[1].proposal_id == "prop-2"
        
        # Verify AI service was called for each proposal
        assert mock_ai.return_value.decide_vote.call_count == 2

    @mock_all_services
    async def test_make_voting_decisions_filters_by_confidence(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test voting decisions filters by confidence threshold."""
        from services.agent_run_service import AgentRunService
        
        # Mock proposals
        proposals = [
            Proposal(
                id="prop-1",
                title="Test Proposal 1",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=1698681600,
                quorum=10.0
            ),
            Proposal(
                id="prop-2",
                title="Test Proposal 2",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x456",
                network="1",
                symbol="TEST",
                scores=[200.0, 25.0],
                scores_total=225.0,
                votes=15,
                created=1698681600,
                quorum=10.0
            )
        ]
        
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.8  # High threshold
        )
        
        # Mock vote decisions with different confidence levels
        mock_vote_decisions = [
            VoteDecision(
                proposal_id="prop-1",
                vote=VoteType.FOR,
                confidence=0.9,  # Above threshold
                reasoning="High confidence reasoning",
                risk_assessment=RiskLevel.LOW,
                strategy_used=VotingStrategy.BALANCED
            ),
            VoteDecision(
                proposal_id="prop-2",
                vote=VoteType.AGAINST,
                confidence=0.6,  # Below threshold
                reasoning="Low confidence reasoning",
                risk_assessment=RiskLevel.HIGH,
                strategy_used=VotingStrategy.BALANCED
            )
        ]
        
        mock_ai.return_value.decide_vote = AsyncMock(side_effect=mock_vote_decisions)
        
        service = AgentRunService()
        result = await service._make_voting_decisions(proposals, preferences)
        
        # Verify only high confidence decision is returned
        assert len(result) == 1
        assert result[0].proposal_id == "prop-1"
        assert result[0].confidence == 0.9

    @mock_all_services
    async def test_make_voting_decisions_processes_all_proposals(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test voting decisions processes all proposals (filtering is done earlier)."""
        from services.agent_run_service import AgentRunService
        
        # Mock proposals
        proposals = [
            Proposal(
                id="prop-1",
                title="Test Proposal 1",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=1698681600,
                quorum=10.0
            ),
            Proposal(
                id="prop-2",
                title="Test Proposal 2",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x456",
                network="1",
                symbol="TEST",
                scores=[200.0, 25.0],
                scores_total=225.0,
                votes=15,
                created=1698681600,
                quorum=10.0
            )
        ]
        
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            blacklisted_proposers=["0x456"]  # This filtering is now done earlier
        )
        
        # Mock vote decisions for both proposals
        mock_vote_decisions = [
            VoteDecision(
                proposal_id="prop-1",
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="Test reasoning 1",
                risk_assessment=RiskLevel.LOW,
                strategy_used=VotingStrategy.BALANCED
            ),
            VoteDecision(
                proposal_id="prop-2",
                vote=VoteType.AGAINST,
                confidence=0.8,
                reasoning="Test reasoning 2",
                risk_assessment=RiskLevel.LOW,
                strategy_used=VotingStrategy.BALANCED
            )
        ]
        
        mock_ai.return_value.decide_vote = AsyncMock(side_effect=mock_vote_decisions)
        
        service = AgentRunService()
        result = await service._make_voting_decisions(proposals, preferences)
        
        # Verify both proposals are processed (filtering happens earlier in workflow)
        assert len(result) == 2
        assert result[0].proposal_id == "prop-1"
        assert result[1].proposal_id == "prop-2"
        
        # Verify AI service was called for both proposals
        assert mock_ai.return_value.decide_vote.call_count == 2

    @mock_all_services
    async def test_make_voting_decisions_empty_proposals(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test voting decisions with empty proposals list."""
        from services.agent_run_service import AgentRunService
        
        preferences = UserPreferences()
        
        service = AgentRunService()
        result = await service._make_voting_decisions([], preferences)
        
        assert result == []
        mock_ai.return_value.decide_vote.assert_not_called()


class TestAgentRunServiceExecuteVotes:
    """Test AgentRunService _execute_votes method."""

    @mock_all_services
    async def test_execute_votes_dry_run(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test vote execution in dry run mode."""
        from services.agent_run_service import AgentRunService
        
        # Mock vote decisions
        decisions = [
            VoteDecision(
                proposal_id="prop-1",
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="Test reasoning",
                risk_assessment=RiskLevel.LOW,
                strategy_used=VotingStrategy.BALANCED
            )
        ]
        
        service = AgentRunService()
        result = await service._execute_votes(decisions, space_id="test-space", dry_run=True)
        
        # Verify result is unchanged in dry run
        assert len(result) == 1
        assert result[0].proposal_id == "prop-1"
        assert result[0].vote == VoteType.FOR
        
        # Verify voting service was not called
        mock_voting.return_value.vote_on_proposal.assert_not_called()

    @mock_all_services
    async def test_execute_votes_actual_voting(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test actual vote execution."""
        from services.agent_run_service import AgentRunService
        
        # Mock vote decisions
        decisions = [
            VoteDecision(
                proposal_id="prop-1",
                vote=VoteType.FOR,
                confidence=0.8,
                reasoning="Test reasoning",
                risk_assessment=RiskLevel.LOW,
                strategy_used=VotingStrategy.BALANCED
            )
        ]
        
        # Mock voting service response
        mock_voting.return_value.vote_on_proposal = AsyncMock(return_value={
            "success": True,
            "transaction_hash": "0xabc123"
        })
        
        service = AgentRunService()
        result = await service._execute_votes(decisions, space_id="test-space", dry_run=False)
        
        # Verify result
        assert len(result) == 1
        assert result[0].proposal_id == "prop-1"
        
        # Verify voting service was called with correct parameters
        mock_voting.return_value.vote_on_proposal.assert_called_once_with(
            space="test-space",
            proposal="prop-1",
            choice=1  # FOR maps to choice 1
        )

    @mock_all_services
    async def test_execute_votes_empty_decisions(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test vote execution with empty decisions list."""
        from services.agent_run_service import AgentRunService
        
        service = AgentRunService()
        result = await service._execute_votes([], space_id="test-space", dry_run=False)
        
        assert result == []
        mock_voting.return_value.vote_on_proposal.assert_not_called()


class TestAgentRunServiceExecuteAgentRun:
    """Test AgentRunService execute_agent_run method."""

    @mock_all_services
    async def test_execute_agent_run_success(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test successful agent run execution."""
        from services.agent_run_service import AgentRunService
        
        # Mock request
        request = AgentRunRequest(
            space_id="test-space",
            dry_run=False
        )
        
        # Mock active proposals
        mock_proposals = [
            Proposal(
                id="prop-1",
                title="Test Proposal 1",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=1698681600,
                quorum=10.0
            )
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
        mock_snapshot.return_value.get_proposals = AsyncMock(return_value=mock_proposals)
        mock_prefs.return_value.load_preferences = AsyncMock(return_value=mock_preferences)
        mock_ai.return_value.decide_vote = AsyncMock(return_value=mock_vote_decision)
        mock_voting.return_value.vote_on_proposal = AsyncMock(return_value={
            "success": True,
            "transaction_hash": "0xabc123"
        })
        
        service = AgentRunService()
        result = await service.execute_agent_run(request)
        
        # Verify result
        assert isinstance(result, AgentRunResponse)
        assert result.space_id == "test-space"
        assert result.proposals_analyzed == 1
        assert len(result.votes_cast) == 1
        assert result.votes_cast[0].proposal_id == "prop-1"
        assert result.user_preferences_applied is True
        assert result.execution_time >= 0.0
        assert result.errors == []

    @mock_all_services
    async def test_execute_agent_run_dry_run(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test agent run execution in dry run mode."""
        from services.agent_run_service import AgentRunService
        
        # Mock request
        request = AgentRunRequest(
            space_id="test-space",
            dry_run=True
        )
        
        # Mock active proposals
        mock_proposals = [
            Proposal(
                id="prop-1",
                title="Test Proposal 1",
                choices=["For", "Against"],
                start=1698768000,
                end=1699372800,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=1698681600,
                quorum=10.0
            )
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
        mock_snapshot.return_value.get_proposals = AsyncMock(return_value=mock_proposals)
        mock_prefs.return_value.load_preferences = AsyncMock(return_value=mock_preferences)
        mock_ai.return_value.decide_vote = AsyncMock(return_value=mock_vote_decision)
        
        service = AgentRunService()
        result = await service.execute_agent_run(request)
        
        # Verify result
        assert isinstance(result, AgentRunResponse)
        assert result.space_id == "test-space"
        assert result.proposals_analyzed == 1
        assert len(result.votes_cast) == 1
        assert result.votes_cast[0].proposal_id == "prop-1"
        assert result.user_preferences_applied is True
        assert result.execution_time >= 0.0
        assert result.errors == []
        
        # Verify voting service was not called in dry run
        mock_voting.return_value.vote_on_proposal.assert_not_called()

    @mock_all_services
    async def test_execute_agent_run_no_active_proposals(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test agent run execution with no active proposals."""
        from services.agent_run_service import AgentRunService
        
        # Mock request
        request = AgentRunRequest(
            space_id="test-space",
            dry_run=False
        )
        
        # Mock user preferences
        mock_preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=3
        )
        
        # Setup mocks
        mock_snapshot.return_value.get_proposals = AsyncMock(return_value=[])
        mock_prefs.return_value.load_preferences = AsyncMock(return_value=mock_preferences)
        
        service = AgentRunService()
        result = await service.execute_agent_run(request)
        
        # Verify result
        assert isinstance(result, AgentRunResponse)
        assert result.space_id == "test-space"
        assert result.proposals_analyzed == 0
        assert len(result.votes_cast) == 0
        assert result.user_preferences_applied is True
        assert result.execution_time >= 0.0
        assert result.errors == []
        
        # Verify AI and voting services were not called
        mock_ai.return_value.decide_vote.assert_not_called()
        mock_voting.return_value.vote_on_proposal.assert_not_called()


class TestAgentRunServiceValidation:
    """Test AgentRunService input validation and error handling."""

    @mock_all_services
    def test_execute_agent_run_none_request(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test execute_agent_run with None request."""
        from services.agent_run_service import AgentRunService
        
        service = AgentRunService()
        
        with pytest.raises(AssertionError, match="Request cannot be None"):
            import asyncio
            asyncio.run(service.execute_agent_run(None))

    @mock_all_services
    def test_fetch_active_proposals_invalid_space_id(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test _fetch_active_proposals with invalid space_id."""
        from services.agent_run_service import AgentRunService
        
        service = AgentRunService()
        
        with pytest.raises(AssertionError, match="Space ID must be non-empty string"):
            import asyncio
            asyncio.run(service._fetch_active_proposals("", 5))

    @mock_all_services
    def test_fetch_active_proposals_invalid_limit(self, mock_snapshot, mock_ai, mock_voting, mock_prefs):
        """Test _fetch_active_proposals with invalid limit."""
        from services.agent_run_service import AgentRunService
        
        service = AgentRunService()
        
        with pytest.raises(AssertionError, match="Limit must be positive integer"):
            import asyncio
            asyncio.run(service._fetch_active_proposals("test-space", 0))