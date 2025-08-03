"""Simple integration test to verify AgentRunService filtering functionality."""

import pytest
import time
from unittest.mock import patch, MagicMock, AsyncMock

from models import (
    AgentRunRequest,
    Proposal,
    UserPreferences,
    VotingStrategy,
)
from services.agent_run_service import AgentRunService
from services.proposal_filter import ProposalFilter


class TestAgentRunServiceFilteringIntegration:
    """Test AgentRunService integration with ProposalFilter."""

    def _create_test_proposal(self, id: str, author: str, scores_total: float = 150.0) -> Proposal:
        """Helper method to create test proposals."""
        current_time = int(time.time())
        return Proposal(
            id=id,
            title=f"Test Proposal {id}",
            choices=["For", "Against"],
            start=current_time - 3600,  # 1 hour ago
            end=current_time + 3600,  # 1 hour from now
            state="active",
            author=author,
            network="1",
            symbol="TEST",
            scores=[scores_total * 0.7, scores_total * 0.3],
            scores_total=scores_total,
            votes=10,
            created=current_time - 7200,  # 2 hours ago
            quorum=10.0
        )

    async def test_filter_and_rank_proposals_method_exists(self):
        """Test that the _filter_and_rank_proposals method exists and is callable."""
        service = AgentRunService()
        
        # Verify method exists
        assert hasattr(service, '_filter_and_rank_proposals')
        assert callable(getattr(service, '_filter_and_rank_proposals'))

    async def test_filter_and_rank_proposals_with_blacklist(self):
        """Test filtering and ranking with blacklisted proposers."""
        service = AgentRunService()
        
        # Create test proposals
        proposals = [
            self._create_test_proposal("prop-1", "0x123"),  # Will be kept
            self._create_test_proposal("prop-2", "0x456"),  # Will be filtered out
            self._create_test_proposal("prop-3", "0x789"),  # Will be kept
        ]
        
        # Create user preferences with blacklist
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=3,
            blacklisted_proposers=["0x456"]
        )
        
        # Test filtering and ranking
        result = await service._filter_and_rank_proposals(proposals, preferences)
        
        # Verify filtering worked
        assert len(result) == 2
        assert all(p.author != "0x456" for p in result)
        assert all(isinstance(p, Proposal) for p in result)
        
        # Verify proposals are ordered (ranked)
        proposal_ids = [p.id for p in result]
        assert "prop-1" in proposal_ids
        assert "prop-3" in proposal_ids
        assert "prop-2" not in proposal_ids

    async def test_filter_and_rank_proposals_with_whitelist(self):
        """Test filtering and ranking with whitelisted proposers."""
        service = AgentRunService()
        
        # Create test proposals
        proposals = [
            self._create_test_proposal("prop-1", "0x123"),  # Will be kept
            self._create_test_proposal("prop-2", "0x456"),  # Will be filtered out
            self._create_test_proposal("prop-3", "0x789"),  # Will be kept
        ]
        
        # Create user preferences with whitelist
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=3,
            whitelisted_proposers=["0x123", "0x789"]
        )
        
        # Test filtering and ranking
        result = await service._filter_and_rank_proposals(proposals, preferences)
        
        # Verify filtering worked
        assert len(result) == 2
        assert all(p.author in ["0x123", "0x789"] for p in result)
        assert all(isinstance(p, Proposal) for p in result)

    async def test_filter_and_rank_proposals_respects_max_proposals(self):
        """Test that filtering respects max_proposals_per_run setting."""
        service = AgentRunService()
        
        # Create more test proposals than the limit
        proposals = [
            self._create_test_proposal("prop-1", "0x123"),
            self._create_test_proposal("prop-2", "0x456"),
            self._create_test_proposal("prop-3", "0x789"),
            self._create_test_proposal("prop-4", "0xabc"),
            self._create_test_proposal("prop-5", "0xdef"),
        ]
        
        # Create user preferences with limit
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=2,  # Limit to 2
            blacklisted_proposers=[]
        )
        
        # Test filtering and ranking
        result = await service._filter_and_rank_proposals(proposals, preferences)
        
        # Verify limit was respected
        assert len(result) == 2
        assert all(isinstance(p, Proposal) for p in result)

    async def test_filter_and_rank_proposals_empty_input(self):
        """Test that filtering handles empty input gracefully."""
        service = AgentRunService()
        
        # Create user preferences
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=3
        )
        
        # Test with empty proposals
        result = await service._filter_and_rank_proposals([], preferences)
        
        # Verify empty result
        assert result == []

    async def test_filter_and_rank_proposals_validation(self):
        """Test that filtering validates input parameters."""
        service = AgentRunService()
        
        # Test with invalid proposals type
        with pytest.raises(AssertionError, match="Proposals must be a list"):
            await service._filter_and_rank_proposals("not_a_list", UserPreferences())
        
        # Test with invalid preferences type
        with pytest.raises(AssertionError, match="Preferences must be UserPreferences"):
            await service._filter_and_rank_proposals([], "not_preferences")

    async def test_proposal_filter_class_integration(self):
        """Test that ProposalFilter class can be used directly."""
        # Create test proposals
        proposals = [
            self._create_test_proposal("prop-1", "0x123"),
            self._create_test_proposal("prop-2", "0x456"),
        ]
        
        # Create user preferences
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=3,
            blacklisted_proposers=["0x456"]
        )
        
        # Test ProposalFilter directly
        proposal_filter = ProposalFilter(preferences)
        
        # Test filtering
        filtered_proposals = proposal_filter.filter_proposals(proposals)
        assert len(filtered_proposals) == 1
        assert filtered_proposals[0].id == "prop-1"
        
        # Test ranking
        ranked_proposals = proposal_filter.rank_proposals(filtered_proposals)
        assert len(ranked_proposals) == 1
        assert ranked_proposals[0].id == "prop-1"
        
        # Test scoring
        score = proposal_filter.calculate_proposal_score(filtered_proposals[0])
        assert isinstance(score, float)
        assert score > 0.0

    async def test_proposal_filter_scoring_algorithm(self):
        """Test that the scoring algorithm works correctly."""
        current_time = int(time.time())
        
        # Create proposals with different characteristics
        urgent_proposal = Proposal(
            id="urgent",
            title="Urgent Proposal",
            choices=["For", "Against"],
            start=current_time - 3600,
            end=current_time + 1800,  # 30 minutes left (more urgent)
            state="active",
            author="0x123",
            network="1",
            symbol="TEST",
            scores=[100.0, 50.0],
            scores_total=150.0,
            votes=10,
            created=current_time - 7200,
            quorum=10.0
        )
        
        less_urgent_proposal = Proposal(
            id="less_urgent",
            title="Less Urgent Proposal",
            choices=["For", "Against"],
            start=current_time - 3600,
            end=current_time + 86400,  # 24 hours left (less urgent)
            state="active",
            author="0x456",
            network="1",
            symbol="TEST",
            scores=[100.0, 50.0],
            scores_total=150.0,
            votes=10,
            created=current_time - 7200,
            quorum=10.0
        )
        
        preferences = UserPreferences()
        proposal_filter = ProposalFilter(preferences)
        
        # Test scoring
        urgent_score = proposal_filter.calculate_proposal_score(urgent_proposal)
        less_urgent_score = proposal_filter.calculate_proposal_score(less_urgent_proposal)
        
        # More urgent proposal should have higher score
        assert urgent_score > less_urgent_score
        assert urgent_score > 0.0
        assert less_urgent_score > 0.0