"""Tests for ProposalFilter following TDD principles.

This test suite drives the implementation of the ProposalFilter class
which provides intelligent filtering and ranking of proposals based on
user preferences and proposal metadata.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from typing import List, Dict, Any
import time

from models import (
    Proposal,
    UserPreferences,
    VotingStrategy,
    VoteDecision,
    VoteType,
    RiskLevel,
)


class TestProposalFilterInitialization:
    """Test ProposalFilter initialization and configuration."""

    def test_proposal_filter_initialization_with_preferences(self):
        """Test ProposalFilter initializes with user preferences."""
        from services.proposal_filter import ProposalFilter
        
        # Create user preferences for testing
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.BALANCED,
            confidence_threshold=0.7,
            max_proposals_per_run=5,
            blacklisted_proposers=["0x123", "0x456"],
            whitelisted_proposers=["0x789", "0xabc"]
        )
        
        # Initialize filter with preferences
        filter_service = ProposalFilter(preferences)
        
        # Runtime assertions for initialization
        assert filter_service.preferences == preferences
        assert filter_service.preferences.voting_strategy == VotingStrategy.BALANCED
        assert filter_service.preferences.confidence_threshold == 0.7
        assert filter_service.preferences.max_proposals_per_run == 5
        assert len(filter_service.preferences.blacklisted_proposers) == 2
        assert len(filter_service.preferences.whitelisted_proposers) == 2

    def test_proposal_filter_initialization_with_default_preferences(self):
        """Test ProposalFilter initializes with default preferences."""
        from services.proposal_filter import ProposalFilter
        
        # Create default preferences
        preferences = UserPreferences()
        
        # Initialize filter with default preferences
        filter_service = ProposalFilter(preferences)
        
        # Runtime assertions for default initialization
        assert filter_service.preferences == preferences
        assert filter_service.preferences.voting_strategy == VotingStrategy.BALANCED
        assert filter_service.preferences.confidence_threshold == 0.7
        assert filter_service.preferences.max_proposals_per_run == 3
        assert len(filter_service.preferences.blacklisted_proposers) == 0
        assert len(filter_service.preferences.whitelisted_proposers) == 0

    def test_proposal_filter_initialization_validates_preferences_type(self):
        """Test ProposalFilter validates preferences type during initialization."""
        from services.proposal_filter import ProposalFilter
        
        # Test with invalid preferences type
        with pytest.raises(AssertionError, match="Preferences must be UserPreferences instance"):
            ProposalFilter("invalid_preferences")
            
        with pytest.raises(AssertionError, match="Preferences must be UserPreferences instance"):
            ProposalFilter(None)
            
        with pytest.raises(AssertionError, match="Preferences must be UserPreferences instance"):
            ProposalFilter({})


class TestProposalFilterFiltering:
    """Test ProposalFilter filtering functionality."""

    def _create_test_proposal(self, id: str, author: str, title: str = "Test Proposal", 
                            start: int = None, end: int = None, state: str = "active") -> Proposal:
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
            scores=[100.0, 50.0],
            scores_total=150.0,
            votes=10,
            created=current_time - 7200,  # 2 hours ago
            quorum=10.0
        )

    def test_filter_proposals_removes_blacklisted_proposers(self):
        """Test filtering removes proposals from blacklisted proposers."""
        from services.proposal_filter import ProposalFilter
        
        # Create test proposals
        proposals = [
            self._create_test_proposal("prop-1", "0x123"),  # Blacklisted
            self._create_test_proposal("prop-2", "0x456"),  # Not blacklisted
            self._create_test_proposal("prop-3", "0x789"),  # Blacklisted
            self._create_test_proposal("prop-4", "0xabc")   # Not blacklisted
        ]
        
        # Create preferences with blacklisted proposers
        preferences = UserPreferences(
            blacklisted_proposers=["0x123", "0x789"]
        )
        
        filter_service = ProposalFilter(preferences)
        filtered_proposals = filter_service.filter_proposals(proposals)
        
        # Runtime assertions for filtering results
        assert len(filtered_proposals) == 2
        assert all(p.author not in ["0x123", "0x789"] for p in filtered_proposals)
        assert filtered_proposals[0].id == "prop-2"
        assert filtered_proposals[1].id == "prop-4"

    def test_filter_proposals_keeps_whitelisted_proposers_when_whitelist_exists(self):
        """Test filtering keeps only whitelisted proposers when whitelist is provided."""
        from services.proposal_filter import ProposalFilter
        
        # Create test proposals
        proposals = [
            self._create_test_proposal("prop-1", "0x123"),  # Whitelisted
            self._create_test_proposal("prop-2", "0x456"),  # Not whitelisted
            self._create_test_proposal("prop-3", "0x789"),  # Whitelisted
            self._create_test_proposal("prop-4", "0xabc")   # Not whitelisted
        ]
        
        # Create preferences with whitelisted proposers
        preferences = UserPreferences(
            whitelisted_proposers=["0x123", "0x789"]
        )
        
        filter_service = ProposalFilter(preferences)
        filtered_proposals = filter_service.filter_proposals(proposals)
        
        # Runtime assertions for whitelist filtering
        assert len(filtered_proposals) == 2
        assert all(p.author in ["0x123", "0x789"] for p in filtered_proposals)
        assert filtered_proposals[0].id == "prop-1"
        assert filtered_proposals[1].id == "prop-3"

    def test_filter_proposals_applies_both_whitelist_and_blacklist(self):
        """Test filtering applies both whitelist and blacklist correctly."""
        from services.proposal_filter import ProposalFilter
        
        # Create test proposals
        proposals = [
            self._create_test_proposal("prop-1", "0x123"),  # Whitelisted
            self._create_test_proposal("prop-2", "0x456"),  # Whitelisted but blacklisted
            self._create_test_proposal("prop-3", "0x789"),  # Not whitelisted
            self._create_test_proposal("prop-4", "0xabc")   # Not whitelisted
        ]
        
        # Create preferences with both whitelist and blacklist
        preferences = UserPreferences(
            whitelisted_proposers=["0x123", "0x456"],
            blacklisted_proposers=["0x456"]  # Blacklist overrides whitelist
        )
        
        filter_service = ProposalFilter(preferences)
        filtered_proposals = filter_service.filter_proposals(proposals)
        
        # Runtime assertions for combined filtering
        assert len(filtered_proposals) == 1
        assert filtered_proposals[0].id == "prop-1"
        assert filtered_proposals[0].author == "0x123"

    def test_filter_proposals_returns_empty_list_for_empty_input(self):
        """Test filtering returns empty list for empty input."""
        from services.proposal_filter import ProposalFilter
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        filtered_proposals = filter_service.filter_proposals([])
        
        assert filtered_proposals == []

    def test_filter_proposals_validates_input_type(self):
        """Test filtering validates input type."""
        from services.proposal_filter import ProposalFilter
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        with pytest.raises(AssertionError, match="Proposals must be a list"):
            filter_service.filter_proposals("not_a_list")
            
        with pytest.raises(AssertionError, match="Proposals must be a list"):
            filter_service.filter_proposals(None)

    def test_filter_proposals_validates_proposal_objects(self):
        """Test filtering validates all items are Proposal objects."""
        from services.proposal_filter import ProposalFilter
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        # Create mixed list with invalid objects
        proposals = [
            self._create_test_proposal("prop-1", "0x123"),
            "not_a_proposal",
            self._create_test_proposal("prop-2", "0x456")
        ]
        
        with pytest.raises(AssertionError, match="All proposals must be Proposal objects"):
            filter_service.filter_proposals(proposals)


class TestProposalFilterRanking:
    """Test ProposalFilter ranking functionality."""

    def _create_test_proposal_with_timing(self, id: str, author: str, 
                                        start: int, end: int, created: int = None) -> Proposal:
        """Helper method to create test proposals with specific timing."""
        return Proposal(
            id=id,
            title=f"Test Proposal {id}",
            choices=["For", "Against"],
            start=start,
            end=end,
            state="active",
            author=author,
            network="1",
            symbol="TEST",
            scores=[100.0, 50.0],
            scores_total=150.0,
            votes=10,
            created=created or start - 3600,
            quorum=10.0
        )

    def test_rank_proposals_by_urgency_time_until_deadline(self):
        """Test ranking proposals by urgency (time until deadline)."""
        from services.proposal_filter import ProposalFilter
        
        current_time = int(time.time())
        
        # Create proposals with different deadlines
        proposals = [
            self._create_test_proposal_with_timing("prop-1", "0x123", 
                                                 current_time - 3600, current_time + 7200),  # 2 hours left
            self._create_test_proposal_with_timing("prop-2", "0x456", 
                                                 current_time - 1800, current_time + 1800),  # 30 minutes left
            self._create_test_proposal_with_timing("prop-3", "0x789", 
                                                 current_time - 3600, current_time + 86400), # 24 hours left
        ]
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        ranked_proposals = filter_service.rank_proposals(proposals)
        
        # Runtime assertions for urgency ranking
        assert len(ranked_proposals) == 3
        assert ranked_proposals[0].id == "prop-2"  # Most urgent (30 minutes left)
        assert ranked_proposals[1].id == "prop-1"  # Medium urgent (2 hours left)
        assert ranked_proposals[2].id == "prop-3"  # Least urgent (24 hours left)

    def test_rank_proposals_considers_voting_power_requirements(self):
        """Test ranking considers proposal voting power requirements."""
        from services.proposal_filter import ProposalFilter
        
        current_time = int(time.time())
        
        # Create proposals with different voting power levels
        proposals = [
            Proposal(
                id="prop-1",
                title="High Power Proposal",
                choices=["For", "Against"],
                start=current_time - 3600,
                end=current_time + 3600,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[1000.0, 500.0],
                scores_total=1500.0,  # High voting power
                votes=50,
                created=current_time - 7200,
                quorum=100.0
            ),
            Proposal(
                id="prop-2",
                title="Low Power Proposal",
                choices=["For", "Against"],
                start=current_time - 3600,
                end=current_time + 3600,
                state="active",
                author="0x456",
                network="1",
                symbol="TEST",
                scores=[50.0, 25.0],
                scores_total=75.0,  # Low voting power
                votes=5,
                created=current_time - 7200,
                quorum=10.0
            )
        ]
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        ranked_proposals = filter_service.rank_proposals(proposals)
        
        # Runtime assertions for voting power consideration
        assert len(ranked_proposals) == 2
        # High power proposal should be ranked higher (more important)
        assert ranked_proposals[0].id == "prop-1"
        assert ranked_proposals[1].id == "prop-2"

    def test_rank_proposals_returns_empty_list_for_empty_input(self):
        """Test ranking returns empty list for empty input."""
        from services.proposal_filter import ProposalFilter
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        ranked_proposals = filter_service.rank_proposals([])
        
        assert ranked_proposals == []

    def test_rank_proposals_validates_input_type(self):
        """Test ranking validates input type."""
        from services.proposal_filter import ProposalFilter
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        with pytest.raises(AssertionError, match="Proposals must be a list"):
            filter_service.rank_proposals("not_a_list")
            
        with pytest.raises(AssertionError, match="Proposals must be a list"):
            filter_service.rank_proposals(None)

    def test_rank_proposals_validates_proposal_objects(self):
        """Test ranking validates all items are Proposal objects."""
        from services.proposal_filter import ProposalFilter
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        # Create mixed list with invalid objects
        proposals = [
            self._create_test_proposal_with_timing("prop-1", "0x123", 
                                                 int(time.time()) - 3600, int(time.time()) + 3600),
            "not_a_proposal"
        ]
        
        with pytest.raises(AssertionError, match="All proposals must be Proposal objects"):
            filter_service.rank_proposals(proposals)


class TestProposalFilterScoring:
    """Test ProposalFilter scoring algorithm."""

    def _create_test_proposal_with_scores(self, id: str, author: str, 
                                        scores_total: float, votes: int,
                                        start: int = None, end: int = None) -> Proposal:
        """Helper method to create test proposals with specific scores."""
        current_time = int(time.time())
        return Proposal(
            id=id,
            title=f"Test Proposal {id}",
            choices=["For", "Against"],
            start=start or current_time - 3600,
            end=end or current_time + 3600,
            state="active",
            author=author,
            network="1",
            symbol="TEST",
            scores=[scores_total * 0.7, scores_total * 0.3],
            scores_total=scores_total,
            votes=votes,
            created=current_time - 7200,
            quorum=10.0
        )

    def test_calculate_proposal_score_considers_urgency(self):
        """Test proposal scoring considers urgency factor."""
        from services.proposal_filter import ProposalFilter
        
        current_time = int(time.time())
        
        # Create proposals with different urgency levels
        urgent_proposal = self._create_test_proposal_with_scores(
            "prop-urgent", "0x123", 100.0, 10,
            start=current_time - 3600, end=current_time + 1800  # 30 minutes left
        )
        
        less_urgent_proposal = self._create_test_proposal_with_scores(
            "prop-less-urgent", "0x456", 100.0, 10,
            start=current_time - 3600, end=current_time + 86400  # 24 hours left
        )
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        urgent_score = filter_service.calculate_proposal_score(urgent_proposal)
        less_urgent_score = filter_service.calculate_proposal_score(less_urgent_proposal)
        
        # Runtime assertions for urgency scoring
        assert isinstance(urgent_score, float)
        assert isinstance(less_urgent_score, float)
        assert urgent_score > less_urgent_score  # More urgent should have higher score

    def test_calculate_proposal_score_considers_voting_power(self):
        """Test proposal scoring considers voting power factor."""
        from services.proposal_filter import ProposalFilter
        
        current_time = int(time.time())
        
        # Create proposals with different voting power
        high_power_proposal = self._create_test_proposal_with_scores(
            "prop-high-power", "0x123", 1000.0, 50,
            start=current_time - 3600, end=current_time + 3600
        )
        
        low_power_proposal = self._create_test_proposal_with_scores(
            "prop-low-power", "0x456", 50.0, 5,
            start=current_time - 3600, end=current_time + 3600
        )
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        high_power_score = filter_service.calculate_proposal_score(high_power_proposal)
        low_power_score = filter_service.calculate_proposal_score(low_power_proposal)
        
        # Runtime assertions for voting power scoring
        assert isinstance(high_power_score, float)
        assert isinstance(low_power_score, float)
        assert high_power_score > low_power_score  # Higher power should have higher score

    def test_calculate_proposal_score_considers_participation_level(self):
        """Test proposal scoring considers participation level factor."""
        from services.proposal_filter import ProposalFilter
        
        current_time = int(time.time())
        
        # Create proposals with different participation levels
        high_participation_proposal = self._create_test_proposal_with_scores(
            "prop-high-participation", "0x123", 100.0, 100,
            start=current_time - 3600, end=current_time + 3600
        )
        
        low_participation_proposal = self._create_test_proposal_with_scores(
            "prop-low-participation", "0x456", 100.0, 5,
            start=current_time - 3600, end=current_time + 3600
        )
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        high_participation_score = filter_service.calculate_proposal_score(high_participation_proposal)
        low_participation_score = filter_service.calculate_proposal_score(low_participation_proposal)
        
        # Runtime assertions for participation scoring
        assert isinstance(high_participation_score, float)
        assert isinstance(low_participation_score, float)
        assert high_participation_score > low_participation_score  # Higher participation should have higher score

    def test_calculate_proposal_score_returns_positive_score(self):
        """Test proposal scoring always returns positive score."""
        from services.proposal_filter import ProposalFilter
        
        current_time = int(time.time())
        
        # Create a basic proposal
        proposal = self._create_test_proposal_with_scores(
            "prop-1", "0x123", 100.0, 10,
            start=current_time - 3600, end=current_time + 3600
        )
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        score = filter_service.calculate_proposal_score(proposal)
        
        # Runtime assertions for positive score
        assert isinstance(score, float)
        assert score > 0.0
        assert score != float('inf')
        assert score == score  # Not NaN

    def test_calculate_proposal_score_validates_input_type(self):
        """Test proposal scoring validates input type."""
        from services.proposal_filter import ProposalFilter
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        with pytest.raises(AssertionError, match="Proposal must be a Proposal object"):
            filter_service.calculate_proposal_score("not_a_proposal")
            
        with pytest.raises(AssertionError, match="Proposal must be a Proposal object"):
            filter_service.calculate_proposal_score(None)


class TestProposalFilterEdgeCases:
    """Test ProposalFilter edge cases and error handling."""

    def test_filter_proposals_handles_tied_scores(self):
        """Test filtering handles proposals with tied scores correctly."""
        from services.proposal_filter import ProposalFilter
        
        current_time = int(time.time())
        
        # Create proposals with identical scores
        proposals = [
            Proposal(
                id="prop-1",
                title="Proposal 1",
                choices=["For", "Against"],
                start=current_time - 3600,
                end=current_time + 3600,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=current_time - 7200,
                quorum=10.0
            ),
            Proposal(
                id="prop-2",
                title="Proposal 2",
                choices=["For", "Against"],
                start=current_time - 3600,
                end=current_time + 3600,
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
        ]
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        # Both filtering and ranking should handle tied scores gracefully
        filtered_proposals = filter_service.filter_proposals(proposals)
        ranked_proposals = filter_service.rank_proposals(filtered_proposals)
        
        # Runtime assertions for tied scores handling
        assert len(filtered_proposals) == 2
        assert len(ranked_proposals) == 2
        assert all(isinstance(p, Proposal) for p in ranked_proposals)

    def test_filter_proposals_handles_expired_proposals(self):
        """Test filtering handles expired proposals correctly."""
        from services.proposal_filter import ProposalFilter
        
        current_time = int(time.time())
        
        # Create mix of active and expired proposals
        proposals = [
            Proposal(
                id="prop-active",
                title="Active Proposal",
                choices=["For", "Against"],
                start=current_time - 3600,
                end=current_time + 3600,  # Active
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=current_time - 7200,
                quorum=10.0
            ),
            Proposal(
                id="prop-expired",
                title="Expired Proposal",
                choices=["For", "Against"],
                start=current_time - 7200,
                end=current_time - 3600,  # Expired
                state="closed",
                author="0x456",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=current_time - 14400,
                quorum=10.0
            )
        ]
        
        preferences = UserPreferences()
        filter_service = ProposalFilter(preferences)
        
        # Filtering should handle expired proposals gracefully
        filtered_proposals = filter_service.filter_proposals(proposals)
        
        # Runtime assertions for expired proposals handling
        assert len(filtered_proposals) == 2  # Both should be returned (filtering by author only)
        assert all(isinstance(p, Proposal) for p in filtered_proposals)

    def test_filter_proposals_handles_large_proposal_lists(self):
        """Test filtering handles large proposal lists efficiently."""
        from services.proposal_filter import ProposalFilter
        
        current_time = int(time.time())
        
        # Create a large list of proposals
        proposals = []
        for i in range(100):
            proposals.append(Proposal(
                id=f"prop-{i}",
                title=f"Proposal {i}",
                choices=["For", "Against"],
                start=current_time - 3600,
                end=current_time + 3600,
                state="active",
                author=f"0x{i:03d}",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=current_time - 7200,
                quorum=10.0
            ))
        
        preferences = UserPreferences(
            max_proposals_per_run=10,
            blacklisted_proposers=[f"0x{i:03d}" for i in range(5)]  # Blacklist first 5
        )
        filter_service = ProposalFilter(preferences)
        
        # Filtering should handle large lists efficiently
        filtered_proposals = filter_service.filter_proposals(proposals)
        ranked_proposals = filter_service.rank_proposals(filtered_proposals)
        
        # Runtime assertions for large list handling
        assert len(filtered_proposals) == 95  # 100 - 5 blacklisted
        assert len(ranked_proposals) == 95
        assert all(isinstance(p, Proposal) for p in ranked_proposals)
        assert all(p.author not in [f"0x{i:03d}" for i in range(5)] for p in filtered_proposals)


class TestProposalFilterIntegration:
    """Test ProposalFilter integration with other components."""

    def test_filter_proposals_integrates_with_user_preferences(self):
        """Test filtering integrates properly with UserPreferences model."""
        from services.proposal_filter import ProposalFilter
        
        current_time = int(time.time())
        
        # Create test proposals
        proposals = [
            Proposal(
                id="prop-1",
                title="Proposal 1",
                choices=["For", "Against"],
                start=current_time - 3600,
                end=current_time + 3600,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=current_time - 7200,
                quorum=10.0
            ),
            Proposal(
                id="prop-2",
                title="Proposal 2",
                choices=["For", "Against"],
                start=current_time - 3600,
                end=current_time + 3600,
                state="active",
                author="0x456",
                network="1",
                symbol="TEST",
                scores=[200.0, 100.0],
                scores_total=300.0,
                votes=20,
                created=current_time - 7200,
                quorum=20.0
            )
        ]
        
        # Create comprehensive preferences
        preferences = UserPreferences(
            voting_strategy=VotingStrategy.CONSERVATIVE,
            confidence_threshold=0.8,
            max_proposals_per_run=5,
            blacklisted_proposers=[],
            whitelisted_proposers=["0x123", "0x456"]
        )
        
        filter_service = ProposalFilter(preferences)
        
        # Test complete filtering and ranking workflow
        filtered_proposals = filter_service.filter_proposals(proposals)
        ranked_proposals = filter_service.rank_proposals(filtered_proposals)
        
        # Runtime assertions for integration
        assert len(filtered_proposals) == 2
        assert len(ranked_proposals) == 2
        assert all(isinstance(p, Proposal) for p in ranked_proposals)
        assert all(p.author in ["0x123", "0x456"] for p in ranked_proposals)

    def test_filter_proposals_provides_metrics_for_response(self):
        """Test filtering provides metrics that can be included in response."""
        from services.proposal_filter import ProposalFilter
        
        current_time = int(time.time())
        
        # Create test proposals
        proposals = [
            Proposal(
                id="prop-1",
                title="Proposal 1",
                choices=["For", "Against"],
                start=current_time - 3600,
                end=current_time + 3600,
                state="active",
                author="0x123",
                network="1",
                symbol="TEST",
                scores=[100.0, 50.0],
                scores_total=150.0,
                votes=10,
                created=current_time - 7200,
                quorum=10.0
            ),
            Proposal(
                id="prop-2",
                title="Proposal 2",
                choices=["For", "Against"],
                start=current_time - 3600,
                end=current_time + 3600,
                state="active",
                author="0x456",  # Will be blacklisted
                network="1",
                symbol="TEST",
                scores=[200.0, 100.0],
                scores_total=300.0,
                votes=20,
                created=current_time - 7200,
                quorum=20.0
            )
        ]
        
        preferences = UserPreferences(
            blacklisted_proposers=["0x456"]
        )
        
        filter_service = ProposalFilter(preferences)
        
        # Test that filtering can provide metrics
        original_count = len(proposals)
        filtered_proposals = filter_service.filter_proposals(proposals)
        ranked_proposals = filter_service.rank_proposals(filtered_proposals)
        
        # Calculate metrics that could be included in response
        filtered_count = len(filtered_proposals)
        ranked_count = len(ranked_proposals)
        blacklisted_count = original_count - filtered_count
        
        # Runtime assertions for metrics
        assert original_count == 2
        assert filtered_count == 1
        assert ranked_count == 1
        assert blacklisted_count == 1
        assert filtered_proposals[0].id == "prop-1"
        assert ranked_proposals[0].id == "prop-1"